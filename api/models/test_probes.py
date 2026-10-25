from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.models import probes
from api.models.misconceptions import default_matcher

REPO = Path(__file__).resolve().parents[2]


def good() -> dict:
    return json.loads((REPO / "data" / "probes.json").read_text(encoding="utf-8"))


def load_with(tmp_path: Path, data: dict) -> dict:
    p = tmp_path / "probes.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return probes.load(p)


def test_the_shipped_probes_load_and_cover_three_entries() -> None:
    loaded = probes.load()
    assert set(loaded) == {"osmosis-inverted-gradient", "newton-force-needed-to-keep-moving", "bonding-sharing-vs-transfer"}


def test_the_correct_answer_is_not_always_in_the_same_place() -> None:
    assert len({p.correct for p, _ in probes.load().values()}) == 3


def test_an_unknown_entry_is_refused(tmp_path: Path) -> None:
    d = good()
    d["probes"][0]["id"] = "no-such-entry"
    with pytest.raises(ValueError, match="no misconception entry"):
        load_with(tmp_path, d)


def test_a_bad_correct_index_is_refused(tmp_path: Path) -> None:
    d = good()
    d["probes"][0]["correct"] = 3
    with pytest.raises(ValueError, match="correct index"):
        load_with(tmp_path, d)


def test_one_option_is_refused(tmp_path: Path) -> None:
    d = good()
    d["probes"][0]["options"] = d["probes"][0]["options"][:1]
    d["probes"][0]["correct"] = 0
    with pytest.raises(ValueError):
        load_with(tmp_path, d)


def test_duplicate_options_are_refused(tmp_path: Path) -> None:
    d = good()
    d["probes"][0]["options"][1] = d["probes"][0]["options"][0]
    with pytest.raises(ValueError, match="same"):
        load_with(tmp_path, d)


@pytest.mark.parametrize("dash", ["—", "–"])
def test_a_dash_in_student_text_is_refused(tmp_path: Path, dash: str) -> None:
    d = good()
    d["probes"][0]["explanation"] += f" and {dash} more"
    with pytest.raises(ValueError, match="dash"):
        load_with(tmp_path, d)


def test_a_duplicate_probe_and_an_extra_field_are_refused(tmp_path: Path) -> None:
    d = good()
    d["probes"].append(d["probes"][0])
    with pytest.raises(ValueError, match="twice"):
        load_with(tmp_path, d)
    d = good()
    d["probes"][0]["hint"] = "x"
    with pytest.raises(ValueError):
        load_with(tmp_path, d)


def test_the_basis_text_never_claims_more_than_the_entry() -> None:
    assert "not checked" in probes.basis_of(False)
    assert "teacher" in probes.basis_of(False)
    assert "was checked against its source" in probes.basis_of(True)


def test_every_entry_the_probes_use_is_unverified_today() -> None:
    assert all(verified is False for _, verified in probes.load().values())


@pytest.mark.parametrize(
    ("question", "entry"),
    [
        ("Is osmosis when water moves to where there is more water?", "osmosis-inverted-gradient"),
        ("Does a moving object need a force to keep moving?", "newton-force-needed-to-keep-moving"),
        ("Are ionic and covalent bonds basically the same kind of sharing?", "bonding-sharing-vs-transfer"),
    ],
)
def test_a_statement_of_the_idea_gets_its_probe(question: str, entry: str) -> None:
    found = probes.probe_for(question)
    assert found is not None and found[0].id == entry


@pytest.mark.parametrize("question", ["What is the capital of France?", "State Ohm's law.", "Write the word equation for photosynthesis."])
def test_an_unrelated_question_gets_none(question: str) -> None:
    assert probes.probe_for(question) is None


def test_the_matcher_is_unchanged_by_loading_probes() -> None:
    assert default_matcher().match("osmosis", top=1)
