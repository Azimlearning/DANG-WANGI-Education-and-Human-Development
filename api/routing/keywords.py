"""A keyword topic finder over the taxonomy's names and hints. Used ONLY by the development fake of the LLM fallback, so offline runs can reach
the right topic for plainly worded questions. It is not the router (it was measured: no better than chance as a second opinion for the model).

Provenance: re-implemented in v4 from eval/models/baselines.py (itself new in v4); topic names and hints come from data/kssm_topics.json.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

TAXONOMY = Path(__file__).resolve().parents[2] / "data" / "kssm_topics.json"
STOP = frozenset(
    "a an and are as at be by can do does for from how in is it its of on or show simulate simulation explain what when where which why with the this that to me my you your i we our their they them than then there these those was were will would about between into using use make let see tell give help understand work works change changes happen happens".split()
)


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1}


@lru_cache(maxsize=1)
def _index() -> tuple[list[str], list[dict[str, float]]]:
    topics = json.loads(TAXONOMY.read_text(encoding="utf-8"))["topics"]
    slugs = [f"{t['subject']}_form{t['form']}_{t['slug']}" for t in topics]
    bags = [_words(t["label"] + " " + t["hint"]) for t in topics]
    df = Counter(w for bag in bags for w in bag)
    return slugs, [{w: math.log(1 + len(bags) / df[w]) for w in bag} for bag in bags]


def best_topic(question: str, min_score: float = 1.0) -> str:
    slugs, weights = _index()
    q = _words(question)
    scores = [sum(wt for w, wt in bag.items() if w in q) for bag in weights]
    best = max(range(len(scores)), key=lambda i: (scores[i], -i))
    return slugs[best] if scores[best] >= min_score else "none"
