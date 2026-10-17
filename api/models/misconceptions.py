"""A misconception matcher: BM25 retrieval over a small, hand-written list. It is retrieval, not a trained model.

Provenance: the list in `data/misconceptions.json` is ported from Synapse v1 (`Synapse/backend/app/knowledge/misconceptions.py`, commit
835a2cefda285b4282ea4d0dbf986d1ff08abdb2); the matcher is new in v4. Five entries cannot train a classifier, so this ranks entries by word overlap
with the question and says how strongly. **First measured 2026-10-18** (refdocs/evidence/2026-10-18-p1b-misconception-matcher.md, a 50-question probe set
written by the same author, so not independent): the right entry came first for all 20 statements of a misconception, but it also fired on 17 of 30
neutral or off-topic questions at the shipped threshold. It is a topic detector. Treat a match as a reason to offer a probe question (P6), never as
a diagnosis.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "misconceptions.json"
K1, B = 1.5, 0.75
STOP = frozenset(
    "a an and are as at be by can do does for from how in is it its of on or the this that to what when where which why with i my me you your".split()
)


def _tokens(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP or len(w) < 2:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                w = w[: -len(suffix)]
                break
        out.append(w)
    return out


@dataclass(frozen=True)
class Match:
    id: str
    score: float
    statement: str
    correct: str
    source: str
    source_verified: bool


class MisconceptionMatcher:
    def __init__(self, entries: list[dict]):
        self.entries = entries
        self._docs = [_tokens(" ".join([e["statement"], e["topic"], *e["triggers"]])) for e in entries]
        self._avg = sum(map(len, self._docs)) / max(1, len(self._docs))
        n = len(self._docs)
        df = Counter(t for d in self._docs for t in set(d))
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self._tf = [Counter(d) for d in self._docs]

    def match(self, question: str, *, top: int = 3, min_score: float = 1.0) -> list[Match]:
        q = _tokens(question)
        scored = []
        for i, e in enumerate(self.entries):
            length = len(self._docs[i])
            score = 0.0
            for t in set(q):
                f = self._tf[i].get(t, 0)
                if f:
                    score += self._idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * length / self._avg))
            if score >= min_score:
                scored.append(
                    Match(e["id"], round(score, 4), e["statement"], e["correct"], e["source"], e["source_verified"])
                )
        scored.sort(key=lambda m: (-m.score, m.id))
        return scored[:top]


@lru_cache(maxsize=1)
def default_matcher() -> MisconceptionMatcher:
    return MisconceptionMatcher(json.loads(DATA.read_text(encoding="utf-8"))["entries"])
