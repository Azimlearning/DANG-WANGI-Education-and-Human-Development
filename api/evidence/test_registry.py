"""The citation registry on a SYNTHETIC corpus (the real one is local and never in a test): what resolves, and every way it must refuse."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.evidence.corpus import Corpus
from api.evidence.registry import CitationBook, RegistryError

DOC = "textbook-physics-synthetic"
SPRING = "In this made-up test passage a coiled wire grows longer in step with the weight it carries, until it is overloaded."
OSMOSIS = "Osmosis is the net movement of water molecules across a partially permeable membrane from a dilute solution to a concentrated solution."


def make(tmp_path: Path, *, pointers: dict | None = None, quotes: dict | None = None) -> CitationBook:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True)
    pages = [{"page": 1, "text": "Contents."}, {"page": 2, "text": f"Hooke's law. {SPRING} More text."}, {"page": 3, "text": OSMOSIS}]
    (corpus_dir / f"{DOC}.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pages), encoding="utf-8")
    default_pointers = {
        "hookes": {
            "doc": DOC, "page": 2, "claim": "extension is proportional to load within the elastic limit",
            "topics": ["physics_f5_elasticity"], "models": ["mechanics.hookes"], "checked_by": "synthetic test",
        },
        "osmosis": {
            "doc": DOC, "page": 3, "claim": "osmosis moves water from dilute to concentrated",
            "topics": ["biology_f4_osmosis"], "models": [], "checked_by": "synthetic test",
        },
    }
    pointer_file = tmp_path / "pointers.json"
    pointer_file.write_text(json.dumps({"pointers": default_pointers if pointers is None else pointers}), encoding="utf-8")
    (corpus_dir / "citations.json").write_text(
        json.dumps({"quotes": {"hookes": SPRING, "osmosis": OSMOSIS} if quotes is None else quotes}), encoding="utf-8"
    )
    return CitationBook.load(Corpus.load(corpus_dir), corpus_dir, pointer_file)


def test_a_citation_that_the_corpus_proves_and_the_plan_matches_resolves_to_a_verified_citation(tmp_path: Path) -> None:
    result = make(tmp_path).resolve(["hookes"], topic="physics_f5_elasticity")
    assert result.ok and result.problems == ()
    (citation,) = result.citations
    assert citation.verified and citation.source == DOC and citation.page == 2 and citation.quote == SPRING
    assert make(tmp_path / "again").evidence.verify(citation)  # the same proof the verifier and the gate run


def test_a_pointer_may_match_by_science_model_instead_of_topic(tmp_path: Path) -> None:
    assert make(tmp_path).resolve(["hookes"], topic="physics_f5_other", models=["mechanics.hookes"]).ok


def test_a_valid_citation_that_does_not_support_this_plan_is_refused(tmp_path: Path) -> None:
    """A planner picking a real but irrelevant id must not earn a label: the Hooke's law quote does not support an osmosis plan."""
    result = make(tmp_path).resolve(["hookes"], topic="biology_f4_osmosis", models=["biology.osmosis_mass"])
    assert not result.ok and result.citations == () and "not this Plan's topic or models" in result.problems[0]


def test_every_way_to_fail_is_named_and_none_gives_a_citation(tmp_path: Path) -> None:
    book = make(tmp_path)
    assert "no such citation" in book.resolve(["nope"], topic="physics_f5_elasticity").problems[0]
    missing_quote = make(tmp_path / "a", quotes={})
    assert "no local quotation" in missing_quote.resolve(["hookes"], topic="physics_f5_elasticity").problems[0]
    paraphrase = make(tmp_path / "b", quotes={"hookes": "A spring stretches in proportion to the load put on it."})
    assert "not on page 2" in paraphrase.resolve(["hookes"], topic="physics_f5_elasticity").problems[0]
    wrong_page = make(
        tmp_path / "c",
        pointers={"hookes": {"doc": DOC, "page": 3, "claim": "x", "topics": ["physics_f5_elasticity"], "checked_by": "t"}},
    )
    assert "not on page 3" in wrong_page.resolve(["hookes"], topic="physics_f5_elasticity").problems[0]
    wrong_doc = make(
        tmp_path / "d",
        pointers={"hookes": {"doc": "no-such-doc", "page": 2, "claim": "x", "topics": ["physics_f5_elasticity"], "checked_by": "t"}},
    )
    assert not wrong_doc.resolve(["hookes"], topic="physics_f5_elasticity").ok


def test_nothing_requested_is_not_ok_and_one_bad_id_among_good_ones_is_not_ok(tmp_path: Path) -> None:
    book = make(tmp_path)
    assert not book.resolve([], topic="physics_f5_elasticity").ok
    mixed = book.resolve(["hookes", "nope"], topic="physics_f5_elasticity")
    assert len(mixed.citations) == 1 and mixed.problems and not mixed.ok  # kit-verified needs EVERY citation to prove


def test_a_missing_pointer_file_or_quotations_file_resolves_nothing_instead_of_guessing(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "empty"
    corpus_dir.mkdir()
    book = CitationBook.load(Corpus.load(corpus_dir), corpus_dir, tmp_path / "absent.json")
    assert not book.resolve(["hookes"], topic="x").ok


def test_a_malformed_pointer_or_quotations_file_is_an_error_not_a_silent_empty_book(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    bad = tmp_path / "pointers.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(RegistryError):
        CitationBook.load(Corpus.load(corpus_dir), corpus_dir, bad)
    bad.write_text(json.dumps({"pointers": {"x": {"doc": "d"}}}), encoding="utf-8")
    with pytest.raises(RegistryError):
        CitationBook.load(Corpus.load(corpus_dir), corpus_dir, bad)
    (corpus_dir / "citations.json").write_text("[]", encoding="utf-8")
    with pytest.raises(RegistryError):
        CitationBook.load(Corpus.load(corpus_dir), corpus_dir, tmp_path / "absent.json")


# ── the committed files: they must agree with each other and hold no textbook text (no corpus needed) ────────────────────────

PLANS = Path(__file__).resolve().parents[2] / "data" / "plans"


def _committed_pointers() -> dict:
    return json.loads((Path(__file__).resolve().parents[2] / "data" / "citations" / "pointers.json").read_text(encoding="utf-8"))["pointers"]


def test_every_committed_plan_cites_only_pointers_that_exist_and_support_it() -> None:
    pointers = _committed_pointers()
    for path in sorted(PLANS.glob("*.json")):
        plan = json.loads(path.read_text(encoding="utf-8"))
        models = {m["model"] for m in plan["models"]}
        assert plan["citation_ids"], f"{path.name} names no citation, so it can never be kit-verified"
        for cid in plan["citation_ids"]:
            assert cid in pointers, f"{path.name}: {cid} is not in data/citations/pointers.json"
            supports = plan["topic"] in pointers[cid]["topics"] or models & set(pointers[cid]["models"])
            assert supports, f"{path.name}: {cid} supports neither its topic nor its models"


def test_the_pointer_file_holds_pointers_not_textbook_text() -> None:
    allowed = {"doc", "page", "claim", "topics", "models", "checked_by", "printed_page"}
    for cid, p in _committed_pointers().items():
        assert set(p) <= allowed and {"doc", "page", "claim", "topics", "checked_by"} <= set(p), cid
        assert len(p["claim"]) <= 200, f"{cid}: a claim is a short note in our words, not a passage"
        assert isinstance(p["page"], int) and p["page"] >= 1 and 1 <= len(cid) <= 24, cid
        assert "NOT yet reviewed by a person" in p["checked_by"] or p["checked_by"].startswith("person"), cid
