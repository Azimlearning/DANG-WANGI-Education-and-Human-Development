"""Baselines the router must beat: the majority class per head, and a keyword rule built from the taxonomy.

Provenance: new in v4. The keyword rule uses only the topic names and short phrasing hints in `data/kssm_topics.json` (no textbook text).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter

from eval.models.data import NONE, TAXONOMY

STOP = frozenset(
    "a an and are as at be by can do does for from how in is it its of on or show simulate simulation explain what when where which why "
    "with the this that to me my you your i we our their they them than then there these those was were will would about between into "
    "using use make let see tell give help understand work works change changes happen happens".split()
)


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


def stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


class Majority:
    def __init__(self, labels: list):
        self.label = Counter(labels).most_common(1)[0][0]

    def predict(self, _query: str):
        return self.label


class KeywordRouter:
    """Scores each topic by how many of its (stemmed) label and hint words appear in the question, weighted by how rare the word is
    across topics. Below `min_score` the answer is `none`. The domain is the winning topic's subject (else the majority domain)."""

    def __init__(self, majority_domain: str, min_score: float = 1.0):
        topics = json.loads(TAXONOMY.read_text(encoding="utf-8"))["topics"]
        self.slugs = [f"{t['subject']}_form{t['form']}_{t['slug']}" for t in topics]
        self.subject = {s: t["subject"] for s, t in zip(self.slugs, topics, strict=True)}
        bags = [{stem(w) for w in words(t["label"] + " " + t["hint"])} for t in topics]
        df = Counter(w for bag in bags for w in bag)
        n = len(bags)
        self.weights = [{w: math.log(1 + n / df[w]) for w in bag} for bag in bags]
        self.majority_domain = majority_domain
        self.min_score = min_score

    def score(self, query: str) -> list[float]:
        q = {stem(w) for w in words(query)}
        return [sum(wt for w, wt in weights.items() if w in q) for weights in self.weights]

    def topic(self, query: str) -> str:
        scores = self.score(query)
        best = max(range(len(scores)), key=lambda i: (scores[i], -i))
        return self.slugs[best] if scores[best] >= self.min_score else NONE

    def domain(self, query: str) -> str:
        t = self.topic(query)
        if t == NONE:
            return self.majority_domain
        s = self.subject[t]
        return {"biology": "biology", "chemistry": "chemistry", "physics": "physics"}.get(s, self.majority_domain)
