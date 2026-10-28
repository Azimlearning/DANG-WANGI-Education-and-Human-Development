"""Citation ids -> citations that the local corpus can re-prove, with the quotations kept OUT of the repository.

A Plan names citations by id (`citation_ids`). Two files say what an id means:

- `data/citations/pointers.json` (committed, no textbook text): for each id, the document and PDF page, what claim it supports, which topics and science
  models it supports, and who checked it. A reviewer opens the page and compares the claim.
- `<CORPUS_DIR>/citations.json` (local, never committed, hard constraint 13): for each id, the quotation (25 to 400 characters, word for word).

`resolve` turns ids into verified `Citation`s, or says exactly why not. Every quotation is re-proved against the corpus text, so a quotation that is not on
that page can never reach a label. A citation is also refused for a Plan it does not support (its topic and models must match the pointer's), so a planner
that picks a valid but irrelevant id cannot earn `kit-verified` (hard constraints 4 and 11). Nothing is guessed and nothing is repaired: any problem means the
caller uses the UNVERIFIED placeholder and the label `model-checked`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from api.evidence.citations import Evidence, UnverifiableCitation, cite
from api.evidence.corpus import Corpus
from api.schema.generated import Citation

REPO = Path(__file__).resolve().parents[2]
DEFAULT_POINTERS = REPO / "data" / "citations" / "pointers.json"
QUOTES_FILE = "citations.json"


def _printed_page(pid: str, p: dict) -> int | None:
    """The book's own page number, or None. A bool, a fraction or a number below 1 is a typo, not a page, so it refuses the file."""
    raw = p.get("printed_page")
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ValueError(f"{pid}: printed_page must be a positive whole number, got {raw!r}")
    return raw


@dataclass(frozen=True)
class Pointer:
    id: str
    doc: str
    page: int
    claim: str
    topics: tuple[str, ...]
    models: tuple[str, ...]
    checked_by: str
    printed_page: int | None = None


@dataclass(frozen=True)
class Resolution:
    citations: tuple[Citation, ...]
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True only when there is at least one citation and every requested id proved. Anything less is not enough for `kit-verified`."""
        return bool(self.citations) and not self.problems


class RegistryError(ValueError):
    pass


class CitationBook:
    def __init__(self, pointers: dict[str, Pointer], quotes: dict[str, str], corpus: Corpus):
        self.pointers = pointers
        self._quotes = quotes
        self.corpus = corpus
        self.evidence = Evidence(corpus)

    @classmethod
    def load(cls, corpus: Corpus, corpus_dir: Path, pointers_path: Path = DEFAULT_POINTERS) -> CitationBook:
        pointers: dict[str, Pointer] = {}
        if pointers_path.exists():
            try:
                raw = json.loads(pointers_path.read_text(encoding="utf-8"))["pointers"]
                for pid, p in raw.items():
                    pointers[pid] = Pointer(
                        id=pid,
                        doc=str(p["doc"]),
                        page=int(p["page"]),
                        claim=str(p["claim"]),
                        topics=tuple(p.get("topics", ())),
                        models=tuple(p.get("models", ())),
                        checked_by=str(p["checked_by"]),
                        printed_page=_printed_page(pid, p),
                    )
            except (ValueError, KeyError, TypeError) as exc:
                raise RegistryError(f"{pointers_path}: not a valid pointer file ({type(exc).__name__}: {exc})") from exc
        quotes: dict[str, str] = {}
        quotes_path = corpus_dir / QUOTES_FILE
        if quotes_path.exists():
            try:
                quotes = {str(k): str(v) for k, v in json.loads(quotes_path.read_text(encoding="utf-8"))["quotes"].items()}
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise RegistryError(f"{quotes_path}: not a valid quotations file ({type(exc).__name__})") from exc
        return cls(pointers, quotes, corpus)

    def resolve(self, ids: list[str], *, topic: str | None = None, models: list[str] | None = None) -> Resolution:
        """The verified citations for `ids`, or the reasons they could not be. `topic` and `models` are the Plan's; a pointer must support at least one."""
        found: list[Citation] = []
        problems: list[str] = []
        used_models = set(models or [])
        for cid in ids:
            pointer = self.pointers.get(cid)
            if pointer is None:
                problems.append(f"{cid}: no such citation in the pointer file")
                continue
            if not ((topic is not None and topic in pointer.topics) or (used_models & set(pointer.models))):
                problems.append(f"{cid}: it supports {list(pointer.topics) or list(pointer.models)}, not this Plan's topic or models")
                continue
            quote = self._quotes.get(cid)
            if quote is None:
                problems.append(f"{cid}: no local quotation for it (the quotations file is missing or lacks this id)")
                continue
            try:
                found.append(cite(self.corpus, pointer.doc, pointer.page, quote, pointer.printed_page))
            except UnverifiableCitation:
                problems.append(f"{cid}: the quotation is not on page {pointer.page} of {pointer.doc}")
        return Resolution(tuple(found), tuple(problems))
