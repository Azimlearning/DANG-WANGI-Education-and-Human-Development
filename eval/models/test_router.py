"""The pure-Python router matches scikit-learn on every held-out question, and the artifact is the one the metrics describe."""

from __future__ import annotations

import json
import os
import socket

import pytest

from api.models import router_model
from api.models.features import char_wb_ngrams, word_ngrams
from eval.models.data import DERIVED, HEADS, load_split


@pytest.fixture(scope="module")
def parity() -> dict:
    return json.loads((DERIVED / "parity.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def model() -> router_model.RouterModel:
    return router_model.load()


def test_the_parity_record_describes_the_shipped_artifact(parity: dict, model: router_model.RouterModel) -> None:
    assert parity["artifact_sha256"] == model.sha256


def test_pure_python_predictions_equal_scikit_learn_on_every_test_question(
    parity: dict, model: router_model.RouterModel
) -> None:
    test = load_split("test")
    assert [r["query"] for r in test] == [r["query"] for r in parity["rows"]]
    mismatches = []
    for row in parity["rows"]:
        got = model.predict(row["query"])
        for head in HEADS:
            label, prob = row[head]
            if str(got[head].label) != str(label) or abs(got[head].confidence - prob) > 1e-4:
                mismatches.append(
                    (row["query"][:50], head, label, str(got[head].label), prob, round(got[head].confidence, 6))
                )
    assert not mismatches, mismatches[:5]


def test_inference_uses_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("network used")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    router_model.load().predict("why does a spring stretch when I hang a weight on it")


def test_a_spring_question_is_routed_to_physics(model: router_model.RouterModel) -> None:
    got = model.predict("Show me how Hooke's law works with a spring and different weights")
    assert got["domain"].label == "physics"
    assert got["topic"].label.startswith("physics_")


def test_probabilities_are_a_distribution(model: router_model.RouterModel) -> None:
    for p in model.predict("what is osmosis").values():
        assert abs(sum(p.probabilities.values()) - 1.0) < 1e-9
        assert p.confidence == max(p.probabilities.values())


def test_a_corrupt_or_edited_artifact_is_refused(tmp_path) -> None:
    data = json.loads(router_model.DEFAULT_ARTIFACT.read_text(encoding="utf-8"))
    data["heads"]["domain"]["intercept"][0] += 1.0
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(router_model.ArtifactError):
        router_model.load(bad)
    with pytest.raises(router_model.ArtifactError):
        router_model.load(tmp_path / "missing.json")


def test_featuriser_matches_scikit_learn_on_awkward_text() -> None:
    from sklearn.feature_extraction.text import CountVectorizer

    texts = ["Hello,  World!!", "a b", "H2O + CO2 -> glucose", "naïve café", "x", "   spaced   out  words "]
    for kind, rng in (("word", (1, 2)), ("char_wb", (3, 5))):
        cv = CountVectorizer(analyzer=kind, ngram_range=rng, lowercase=True)
        for t in texts:
            ours = word_ngrams(t, *rng) if kind == "word" else char_wb_ngrams(t, *rng)
            assert sorted(ours) == sorted(cv.build_analyzer()(t)), (kind, t)


@pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="retrains twice (about 4 minutes); set RUN_SLOW=1")
def test_training_twice_gives_identical_artifact_bytes() -> None:
    from eval.models import train_router

    first = json.dumps(train_router.export(train_router.fit_all()), sort_keys=True)
    second = json.dumps(train_router.export(train_router.fit_all()), sort_keys=True)
    assert first == second
