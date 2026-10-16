"""The local textbook corpus and the one thing it is for: proving that a quotation is on a page (hard constraint 4).

The corpus is NEVER in the repository (hard constraint 13: no textbook PDFs or extracted passages). It lives in a folder the owner chooses
(`CORPUS_DIR`), one file per document, `<doc_id>.jsonl`, one line per page: `{"page": 12, "text": "..."}`. `api/evidence/ingest.py` builds it from PDFs on the
owner's machine. Tests use small SYNTHETIC documents made up for the purpose.

Retrieval is BM25 over page windows (A-9: dense embeddings only if measured to help). `verify_quote` is exact after normalisation, so a paraphrase or a
mis-remembered quotation can never be marked verified; it is what the verifier re-runs for a `kit-verified` label.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_STOP = frozenset("a an and are as at be by for from in is it its of on or the this that to was were with".split())
MIN_QUOTE_CHARS = 25
MAX_QUOTE_CHARS = 400
WINDOW_WORDS = 60
STRIDE_WORDS = 30
K1, B = 1.5, 0.75


def normalise(text: str) -> str:
    """Case, accents, ligatures, dashes, quotes and spacing folded, so a quotation survives a PDF's typography but not a changed word."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-").replace("−", "-")
    text = re.sub(r"[‘’‚‛]", "'", text)
    text = re.sub(r"[“”„‟]", '"', text)
    text = re.sub(r"-\s*\n\s*", "", text)  # a word split across lines by a hyphen
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", normalise(text)) if w not in _STOP and len(w) > 1]


@dataclass(frozen=True)
class Hit:
    doc: str
    page: int
    score: float
    snippet: str


class CorpusError(ValueError):
    pass


class Corpus:
    def __init__(self, pages: dict[str, dict[int, str]]):
        self._pages = {doc: {int(p): t for p, t in by.items()} for doc, by in pages.items()}
        self._normalised = {doc: {p: normalise(t) for p, t in by.items()} for doc, by in self._pages.items()}
        self._windows: list[tuple[str, int, list[str], str]] = []
        for doc, by in self._pages.items():
            for page, text in by.items():
                words = text.split()
                for start in range(0, max(1, len(words)), STRIDE_WORDS):
                    chunk = " ".join(words[start : start + WINDOW_WORDS])
                    if chunk:
                        self._windows.append((doc, page, _tokens(chunk), chunk))
                    if start + WINDOW_WORDS >= len(words):
                        break
        n = len(self._windows)
        df = Counter(t for _, _, toks, _ in self._windows for t in set(toks))
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self._avg = sum(len(toks) for _, _, toks, _ in self._windows) / max(1, n)

    @classmethod
    def load(cls, directory: Path) -> Corpus:
        if not directory.is_dir():
            raise CorpusError(f"the corpus folder {directory} does not exist")
        pages: dict[str, dict[int, str]] = {}
        for path in sorted(directory.glob("*.jsonl")):
            by: dict[int, str] = {}
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    by[int(row["page"])] = str(row["text"])
                except (ValueError, KeyError, TypeError) as exc:
                    raise CorpusError(f'{path.name} line {n}: expected {{"page": int, "text": str}}') from exc
            pages[path.stem] = by
        return cls(pages)

    @property
    def documents(self) -> list[str]:
        return sorted(self._pages)

    def page_count(self, doc: str) -> int:
        return len(self._pages.get(doc, {}))

    def verify_quote(self, doc: str, page: int, quote: str) -> bool:
        """True only if `quote` (25 to 400 characters, after normalisation) appears verbatim on that page of that document."""
        q = normalise(quote)
        if not MIN_QUOTE_CHARS <= len(q) <= MAX_QUOTE_CHARS:
            return False
        text = self._normalised.get(doc, {}).get(page)
        return text is not None and q in text

    def search(self, query: str, *, k: int = 5) -> list[Hit]:
        q = set(_tokens(query))
        scored = []
        for doc, page, toks, chunk in self._windows:
            tf = Counter(toks)
            length = len(toks) or 1
            score = sum(
                self._idf.get(t, 0.0) * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * length / self._avg))
                for t in q
                if t in tf
            )
            if score > 0:
                scored.append(Hit(doc, page, round(score, 4), chunk))
        scored.sort(key=lambda h: (-h.score, h.doc, h.page))
        best: dict[tuple[str, int], Hit] = {}
        for h in scored:
            best.setdefault((h.doc, h.page), h)
        return list(best.values())[:k]
