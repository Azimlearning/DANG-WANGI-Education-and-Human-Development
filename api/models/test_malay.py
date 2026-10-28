"""Questions in Bahasa Melayu for the English-trained router (W13, D-63)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from api.models import malay, router_model
from api.routing import router

REPO = Path(__file__).resolve().parents[2]
ROUTER_DATA = REPO / "data" / "models" / "router"


def test_a_malay_question_is_recognised_and_an_english_one_never_is() -> None:
    for q in (
        "Mengapa spring boleh memanjang bila kita gantung pemberat?",
        "Bagaimana mengira pembesaran sebuah sel di bawah mikroskop?",
        "Berapakah bilangan mol dalam dua puluh gram air?",
        "macam mana nak calculate current kalau resistance naik?",
        "terangkan hukum Hooke",
    ):
        assert malay.is_malay(q), q
    # None of the 3,000 English questions the router was built from reads as Malay: a false positive would translate an English question for nothing.
    english = [json.loads(line)["query"] for name in ("train", "val", "test") for line in (ROUTER_DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(english) > 2500
    assert [q for q in english if malay.is_malay(q)] == []


@pytest.mark.parametrize("q", ["How does air pressure change with depth?", "What is a gas?", "Why does the water level rise in a cell?", "Explain the law of Hooke", ""])
def test_english_and_empty_questions_are_not_malay(q: str) -> None:
    assert not malay.is_malay(q)


def test_words_phrases_and_affixed_words_are_translated() -> None:
    t = malay.to_english("Mengapa pemanjangan spring bertambah apabila beban dinaikkan?")
    assert t.text.startswith("why extension spring increase when load ")
    assert "raised" in t.text or "raise" in t.text
    assert malay.to_english("beza keupayaan dan separuh hayat").text == "potential difference voltage and half-life"
    assert malay.to_english("menyejukkan air").text == "cool water"  # meny- + sejuk + -kan
    assert malay.to_english("pemanasan global").text == "global warming"


def test_the_words_it_did_not_understand_are_counted_against_the_question() -> None:
    clear = malay.to_english("Mengapa pemanjangan spring bertambah apabila beban dinaikkan?")
    assert clear.coverage == 1.0
    blurry = malay.to_english("Mengapa kemonceng berlegar apabila perkhemahan berlangsung dengan hebat?")
    assert blurry.coverage < malay.MIN_COVERAGE
    # An English word the router knows is understood; the same word the router does not know is not.
    assert malay.to_english("apakah gravity", known=lambda w: w == "gravity").understood == 2
    assert malay.to_english("apakah gravity", known=lambda w: False).understood == 1


def test_the_glossary_has_no_empty_key_and_no_duplicate_meaning_trap() -> None:
    g = malay.glossary()
    assert "" not in g.words
    assert g.words["mengapa"] == "why"
    # A Malay marker is never also an English word: a question using it is Malay.
    english_words = {"and", "at", "in", "for", "of", "the", "is", "a", "to", "or", "by", "all", "can", "not"}
    assert not (set(g.markers) & english_words)


@pytest.fixture(scope="module")
def model() -> router_model.RouterModel:
    return router_model.default_model()


def test_a_malay_question_is_routed_from_its_translation(model: router_model.RouterModel) -> None:
    decision = asyncio.run(router.route("Bagaimana frekuensi dan panjang gelombang menentukan laju gelombang?", model=model))
    assert decision.topic.value == "physics_form4_waves" and decision.topic.source == "local"
    assert decision.english.startswith("how frequency and wavelength determine")


def test_an_english_question_is_read_as_it_is(model: router_model.RouterModel) -> None:
    q = "How does the speed of a wave depend on frequency and wavelength?"
    prepared = router.prepare(q, model)
    assert prepared.language == "en" and prepared.query == q and prepared.trusted
    assert asyncio.run(router.route(q, model=model)).english == q


def test_a_malay_question_the_glossary_cannot_read_goes_to_the_fallback_on_every_head(model: router_model.RouterModel) -> None:
    q = "Mengapa kemonceng berlegar apabila perkhemahan berlangsung dengan hebat?"
    prepared = router.prepare(q, model)
    assert prepared.language == "ms" and not prepared.trusted
    decision = asyncio.run(router.route(q, model=model))
    assert decision.topic.source == "default" and decision.topic.value == "none"  # no fallback model here: a flagged default, never a guess
    assert decision.domain.source == decision.pattern.source == decision.complexity.source == "default"


def test_the_probe_set_keeps_its_promise(model: router_model.RouterModel) -> None:
    """The guard answers more Malay questions from the library and none of the ones it answers is wrong (on the probe: written by the author of the glossary, so optimistic)."""
    from eval.models.bm_probe import load_probe, score

    rows = load_probe()
    assert len(rows) == 68
    guarded = score(model, rows)["all"]
    unguarded = score(model, rows, guarded=False)["all"]
    assert guarded["right_when_answered"] == 1.0 and unguarded["right_when_answered"] == 1.0
    assert guarded["answered_from_library"] > 2 * unguarded["answered_from_library"]
    assert guarded["topic_accuracy"] >= 0.7
