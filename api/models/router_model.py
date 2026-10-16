"""Pure-Python inference for the multi-head router artifact (router-v1.json). No numpy, no scikit-learn, no network.

Provenance: new in v4 (D-20). The artifact is written by `eval/models/train_router.py`; this module reads it and reproduces the
training library's predictions (proved by eval/models/test_router.py against `data/models/router/parity.json`).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from api.models.features import analyse, tfidf

DEFAULT_ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "router-v1.json"


class ArtifactError(ValueError):
    """The artifact is missing, malformed, or its content hash does not match."""


@dataclass(frozen=True)
class HeadPrediction:
    label: str | int
    confidence: float
    probabilities: dict[str, float]


class RouterModel:
    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.sha256: str = data["content_sha256"]
        self._features = []
        for f in data["features"]:
            self._features.append(
                (
                    f["kind"],
                    tuple(f["ngram_range"]),
                    {t: i for i, t in enumerate(f["terms"])},
                    f["idf"],
                    f["offset"],
                )
            )
        self.heads: dict[str, list[str | int]] = {}
        self._intercept: dict[str, list[float]] = {}
        # Per head, weights indexed by feature so scoring touches only the features a question has.
        self._by_feature: dict[str, dict[int, list[tuple[int, float]]]] = {}
        for head, h in data["heads"].items():
            self.heads[head] = list(h["classes"])
            self._intercept[head] = list(h["intercept"])
            index: dict[int, list[tuple[int, float]]] = {}
            for k, row in enumerate(h["weights"]):
                for feature, weight in row:
                    index.setdefault(feature, []).append((k, weight))
            self._by_feature[head] = index

    def features(self, query: str) -> dict[int, float]:
        merged: dict[int, float] = {}
        for kind, ngram_range, vocabulary, idf, offset in self._features:
            counts = Counter(analyse(kind, query, ngram_range))
            for i, v in tfidf(counts, vocabulary, idf).items():
                merged[offset + i] = v
        return merged

    def predict(self, query: str) -> dict[str, HeadPrediction]:
        x = self.features(query)
        out: dict[str, HeadPrediction] = {}
        for head, classes in self.heads.items():
            scores = list(self._intercept[head])
            index = self._by_feature[head]
            for feature, value in x.items():
                for k, weight in index.get(feature, ()):
                    scores[k] += value * weight
            top = max(scores)
            exps = [math.exp(s - top) for s in scores]
            total = sum(exps)
            probs = [e / total for e in exps]
            best = max(range(len(classes)), key=lambda k: (probs[k], -k))
            out[head] = HeadPrediction(
                classes[best], probs[best], {str(c): p for c, p in zip(classes, probs, strict=True)}
            )
        return out


def verify_hash(data: dict) -> None:
    claimed = data.get("content_sha256")
    body = {k: v for k, v in data.items() if k != "content_sha256"}
    actual = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if claimed != actual:
        raise ArtifactError("router artifact hash mismatch: the file was edited or is corrupt")


def load(path: Path = DEFAULT_ARTIFACT) -> RouterModel:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read router artifact {path}: {exc}") from exc
    if data.get("format") != 1:
        raise ArtifactError(f"unsupported router artifact format {data.get('format')!r}")
    verify_hash(data)
    return RouterModel(data)


@lru_cache(maxsize=1)
def default_model() -> RouterModel:
    return load()
