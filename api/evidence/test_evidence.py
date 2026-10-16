"""The evidence engine on SYNTHETIC documents (made up for these tests; the real corpus is never in the repository), and the labels it unlocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.evidence.citations import Evidence, UnverifiableCitation, cite
from api.evidence.corpus import Corpus, CorpusError, normalise
from api.schema.generated import Citation
from api.verify.gate import deliver
from api.verify.mint import VerificationFailed, guard_label, verify_environment
from api.verify.store import SqliteEnvironmentStore

PAGES = {
    "synthetic-physics": {
        7: "A spring obeys the law of the synthetic textbook: the extension is proportional to the load, provided the elastic limit is not exceeded.",
        8: "Pressure in a liquid increases with depth. Nothing else on this page is about springs.",
    },
    "synthetic-biology": {
        3: "Cells of a made up organism are small because the surface area to volume ratio falls as they grow."
    },
}
QUOTE = "the extension is proportional to the load"


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return Corpus(PAGES)


def test_a_quotation_is_verified_only_if_it_is_on_that_page(corpus: Corpus) -> None:
    assert corpus.verify_quote("synthetic-physics", 7, QUOTE + ", provided the elastic limit")
    assert not corpus.verify_quote("synthetic-physics", 8, QUOTE + ", provided")  # right words, wrong page
    assert not corpus.verify_quote("synthetic-biology", 7, QUOTE + ", provided")  # wrong document
    assert not corpus.verify_quote(
        "synthetic-physics", 7, "the extension is inversely proportional to the load"
    )  # one word changed
    assert not corpus.verify_quote("synthetic-physics", 7, "extension")  # too short to prove anything
    assert not corpus.verify_quote("synthetic-physics", 7, "x" * 500)


def test_typography_is_folded_but_words_are_not() -> None:
    assert normalise("The  load\nis—proportional’s") == normalise("the load is-proportional's")
    assert normalise("exten-\nsion") == "extension"
    c = Corpus({"d": {1: "The “extension” is proportional to the load, within the limit."}})
    assert c.verify_quote("d", 1, 'the "extension" is proportional to the load')


def test_search_finds_the_page_that_talks_about_the_question(corpus: Corpus) -> None:
    hits = corpus.search("why does a spring stretch with load")
    assert hits and (hits[0].doc, hits[0].page) == ("synthetic-physics", 7)
    assert corpus.search("zzzz qqqq") == []


def test_cite_returns_a_verified_citation_or_refuses(corpus: Corpus) -> None:
    c = cite(corpus, "synthetic-physics", 7, QUOTE + ", provided")
    assert (c.verified, c.page, c.source) == (True, 7, "synthetic-physics")
    with pytest.raises(UnverifiableCitation):
        cite(corpus, "synthetic-physics", 8, QUOTE + ", provided")


def test_corpus_loading_validates_its_files(tmp_path: Path) -> None:
    (tmp_path / "doc.jsonl").write_text(
        json.dumps({"page": 1, "text": "some synthetic words here for the test"}) + "\n", encoding="utf-8"
    )
    assert Corpus.load(tmp_path).documents == ["doc"]
    (tmp_path / "bad.jsonl").write_text("not json\n", encoding="utf-8")
    with pytest.raises(CorpusError):
        Corpus.load(tmp_path)
    with pytest.raises(CorpusError):
        Corpus.load(tmp_path / "missing")


# ── labels ──────────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_kit_verified_needs_every_citation_re_proved_and_not_the_free_lane(corpus: Corpus) -> None:
    good = cite(corpus, "synthetic-physics", 7, QUOTE + ", provided")
    ev = Evidence(corpus)
    guard_label("instantiate", "kit-verified", (good,), ev)  # allowed
    with pytest.raises(VerificationFailed) as err:
        guard_label("free", "kit-verified", (good,), ev)
    assert err.value.rule == "free_lane"
    with pytest.raises(VerificationFailed) as err:
        guard_label("instantiate", "kit-verified", (good,), None)
    assert err.value.rule in ("citation_unproved", "no_evidence")
    placeholder = Citation(source="UNVERIFIED", page=None, quote=None, verified=False)
    with pytest.raises(VerificationFailed) as err:
        guard_label("instantiate", "kit-verified", (good, placeholder), ev)
    assert err.value.rule == "ungrounded"


def test_a_verified_flag_that_cannot_be_re_proved_is_refused_even_for_model_checked(corpus: Corpus) -> None:
    forged = Citation(
        source="synthetic-physics", page=7, quote="the extension is inversely proportional to the load", verified=True
    )
    with pytest.raises(VerificationFailed) as err:
        guard_label("instantiate", "model-checked", (forged,), Evidence(corpus))
    assert err.value.rule == "citation_unproved"
    with pytest.raises(VerificationFailed):
        guard_label("instantiate", "model-checked", (forged,), None)  # no corpus: the claim cannot be proved


def test_reviewed_and_canonical_still_need_a_person(corpus: Corpus) -> None:
    good = cite(corpus, "synthetic-physics", 7, QUOTE + ", provided")
    for label in ("reviewed", "canonical"):
        with pytest.raises(VerificationFailed) as err:
            guard_label("instantiate", label, (good,), Evidence(corpus))
        assert err.value.rule == "needs_human"


def test_end_to_end_a_kit_verified_environment_is_minted_stored_and_delivered_then_refused_without_the_corpus(
    corpus: Corpus, kit_dist: Path, kit_version: str, tmp_path: Path
) -> None:
    from api.verify.conftest import fixture_html

    ev = Evidence(corpus)
    citation = cite(corpus, "synthetic-physics", 7, QUOTE + ", provided")
    env = verify_environment(
        slug="reference-spring",
        title="Why does a spring stretch?",
        raw_html=fixture_html("reference-spring.html"),
        lane="instantiate",
        label="kit-verified",
        kit_version=kit_version,
        citations=[citation],
        plan_summary="A synthetic-corpus test.",
        public_origin="http://localhost:3000",
        kit_dist=kit_dist,
        interaction_seconds=1.0,
        plan_models=[{"id": "mechanics.hookes", "params": {"k": 50}}],
        evidence=ev,
    )
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_verified(env)
    block = deliver(store, env.env_id, public_origin="http://localhost:3000", kit_dist=kit_dist, evidence=ev)
    assert (
        block.label == "kit-verified"
        and block.citations[0].verified
        and "verified textbook source" in block.checked.limits
    )
    # The corpus is gone or changed: the gate re-proves the citation and refuses.
    with pytest.raises(VerificationFailed) as err:
        deliver(store, env.env_id, public_origin="http://localhost:3000", kit_dist=kit_dist, evidence=None)
    assert err.value.stage == "gate"
    with pytest.raises(VerificationFailed):
        deliver(
            store,
            env.env_id,
            public_origin="http://localhost:3000",
            kit_dist=kit_dist,
            evidence=Evidence(Corpus({"synthetic-physics": {7: "different words"}})),
        )
