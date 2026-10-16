from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.evidence import catalogue as cat
from api.evidence.corpus import Corpus


def test_the_shipped_catalogue_is_valid_and_every_authored_entry_has_its_plan() -> None:
    c = cat.load()
    assert cat.problems(c) == []
    assert len(c.entries) >= 5 and all(e.status == "authored" for e in c.entries)
    assert all(not e.confirmed_by_person and e.source is None for e in c.entries), (
        "nothing is matched to the owner's documents yet"
    )


def test_the_schema_is_strict() -> None:
    base = cat.load().entries[0].model_dump(mode="json")
    with pytest.raises(ValidationError):
        cat.Entry.model_validate({**base, "surprise": 1})
    with pytest.raises(ValidationError):
        cat.Entry.model_validate({**base, "form": 6})
    with pytest.raises(ValidationError):
        cat.Entry.model_validate({**base, "status": "done"})


def test_problems_are_reported_for_inconsistent_entries(tmp_path: Path) -> None:
    good = cat.load().entries[0]
    broken = [
        good,
        good,  # duplicate
        good.model_copy(update={"id": "x_missing_plan", "plan_id": "no_such_plan"}),
        good.model_copy(update={"id": "x_wrong_topic", "topic": "physics_form5_electricity"}),
        good.model_copy(update={"id": "x_conf", "status": "confirmed"}),
        good.model_copy(update={"id": "x_prop", "status": "proposed", "confirmed_by_person": True}),
    ]
    text = "\n".join(cat.problems(cat.Catalogue.model_construct(version=1, entries=broken)))
    for needle in (
        "duplicate id",
        "does not exist",
        "does not match subject",
        "needs confirmed_by_person",
        "cannot be marked confirmed",
    ):
        assert needle in text


def test_proposals_from_a_synthetic_corpus_are_never_treated_as_real() -> None:
    corpus = Corpus(
        {
            "synthetic-lab-book": {
                4: "Experiment 3.2 Rate of a made up reaction\nAim: To find how a made up quantity changes with time. More words here.\n",
                5: "Just prose without any heading on this page about nothing in particular.",
            }
        }
    )
    found = cat.propose_from_corpus(corpus, "chemistry", 4)
    assert len(found) == 1 and found[0].status == "proposed" and not found[0].confirmed_by_person
    assert found[0].source == cat.Source(doc="synthetic-lab-book", page=4) and "made up quantity" in found[0].aim
    assert cat.problems(cat.Catalogue(version=1, entries=found)) == []


def test_the_catalogue_file_holds_metadata_not_textbook_text() -> None:
    data = json.loads(cat.CATALOGUE.read_text(encoding="utf-8"))
    assert all(len(e["aim"]) <= 240 and e["source"] is None for e in data["entries"])
