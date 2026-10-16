"""Pure-Python text features for the router, written to reproduce scikit-learn's TfidfVectorizer exactly for the settings the router uses
(lowercase, default word token pattern, word n-grams or `char_wb` n-grams, sublinear tf, smoothed idf, L2 norm). No heavy dependency at
inference. The parity test (eval/models/test_router.py) proves the two agree on every test question.

Provenance: new in v4. Behaviour follows scikit-learn 1.9.x `CountVectorizer._word_ngrams`, `_char_wb_ngrams` and `TfidfTransformer`.
"""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN = re.compile(r"(?u)\b\w\w+\b")


def word_ngrams(text: str, low: int, high: int) -> list[str]:
    tokens = TOKEN.findall(text.lower())
    if high == 1:
        return tokens
    grams = list(tokens) if low == 1 else []
    for n in range(max(2, low), min(high, len(tokens)) + 1):
        grams += [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    return grams


def char_wb_ngrams(text: str, low: int, high: int) -> list[str]:
    text = re.sub(r"\s\s+", " ", text.lower())  # scikit-learn normalises runs of whitespace first
    grams: list[str] = []
    for word in text.split():
        padded = " " + word + " "
        width = len(padded)
        for n in range(low, high + 1):
            offset = 0
            grams.append(padded[offset : offset + n])
            while offset + n < width:
                offset += 1
                grams.append(padded[offset : offset + n])
            if offset == 0:  # a word shorter than n gives one gram; scikit-learn stops at the next n
                break
    return grams


def analyse(kind: str, text: str, ngram_range: tuple[int, int]) -> list[str]:
    if kind == "word":
        return word_ngrams(text, *ngram_range)
    if kind == "char_wb":
        return char_wb_ngrams(text, *ngram_range)
    raise ValueError(f"unknown analyzer {kind!r}")


def tfidf(counts: Counter, vocabulary: dict[str, int], idf: list[float]) -> dict[int, float]:
    """Sublinear tf times idf over the known vocabulary, L2-normalised, as a sparse {index: value}."""
    weights = {
        vocabulary[term]: (1.0 + math.log(c)) * idf[vocabulary[term]]
        for term, c in counts.items()
        if term in vocabulary
    }
    norm = math.sqrt(sum(v * v for v in weights.values()))
    return {i: v / norm for i, v in weights.items()} if norm > 0 else {}
