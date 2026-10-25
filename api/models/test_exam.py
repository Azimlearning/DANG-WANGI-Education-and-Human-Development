from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.models import exam

REPO = Path(__file__).resolve().parents[2]


def good() -> dict:
    return json.loads((REPO / "data" / "exam_items.json").read_text(encoding="utf-8"))


def load_with(tmp_path: Path, data: dict) -> dict:
    p = tmp_path / "items.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return exam.load(p)


def item(item_id: str) -> exam.Item:
    return next(i for i in exam.default_items().values() if i.id == item_id)


def test_the_shipped_items_load_and_every_sample_answer_earns_every_mark() -> None:
    items = exam.default_items()
    assert len(items) == 6
    for it in items.values():
        assert exam.mark(it, it.sample) == (it.marks, [True] * it.marks)


def test_an_empty_answer_earns_nothing_and_the_score_never_exceeds_the_total() -> None:
    for it in exam.default_items().values():
        assert exam.mark(it, "") == (0, [False] * it.marks)
        assert exam.mark(it, it.sample * 5)[0] == it.marks


def test_marking_ignores_case_punctuation_and_word_endings() -> None:
    hooke = item("hookes-law-short")
    assert exam.mark(hooke, "THE EXTENSION IS DIRECTLY PROPORTIONAL TO THE LOAD!")[1][0]
    assert exam.mark(hooke, "When the load doubles, the extension doubles")[1][0]


def test_a_related_but_wrong_answer_does_not_earn_the_point() -> None:
    hooke = item("hookes-law-short")
    assert not exam.mark(hooke, "The extension is inversely related to the load")[1][0]
    wave = item("wave-speed-short")
    assert exam.mark(wave, "speed = frequency x wavelength = 50 x 2 = 200 m/s") == (2, [True, True, False])


def test_a_digit_stem_needs_the_whole_number() -> None:
    wave = item("wave-speed-short")
    assert not exam.mark(wave, "the speed is 1000")[1][2]
    assert exam.mark(wave, "the speed is 100")[1][2]


def test_a_graph_answer_needs_the_origin() -> None:
    hooke = item("hookes-law-short")
    assert not exam.mark(hooke, "the graph is a straight line")[1][1]
    assert exam.mark(hooke, "a straight line through the origin")[1][1]


def test_osmosis_needs_the_direction_not_just_the_word() -> None:
    o = item("osmosis-potato-short")
    assert exam.mark(o, "osmosis happens")[1] == [False, True, False]


def test_an_unknown_topic_is_refused(tmp_path: Path) -> None:
    d = good()
    d["items"][0]["topic"] = "physics_form9_nothing"
    with pytest.raises(ValueError, match="not a topic"):
        load_with(tmp_path, d)


def test_two_items_for_one_topic_are_refused(tmp_path: Path) -> None:
    d = good()
    d["items"][1]["topic"] = d["items"][0]["topic"]
    with pytest.raises(ValueError, match="already has an item"):
        load_with(tmp_path, d)


def test_a_sample_that_does_not_earn_full_marks_is_refused(tmp_path: Path) -> None:
    d = good()
    d["items"][0]["points"][0]["wordings"] = [["zzzzzz"]]
    with pytest.raises(ValueError, match="sample answer earns"):
        load_with(tmp_path, d)


def test_an_empty_wording_and_a_bad_stem_are_refused(tmp_path: Path) -> None:
    d = good()
    d["items"][0]["points"][0]["wordings"] = [[]]
    with pytest.raises(ValueError):
        load_with(tmp_path, d)
    d = good()
    d["items"][0]["points"][0]["wordings"] = [["Has Space"]]
    with pytest.raises(ValueError):
        load_with(tmp_path, d)


@pytest.mark.parametrize("dash", ["—", "–"])
def test_a_dash_in_student_text_is_refused(tmp_path: Path, dash: str) -> None:
    d = good()
    d["items"][0]["stem"] += f" and {dash} more"
    with pytest.raises(ValueError, match="dash"):
        load_with(tmp_path, d)


def test_a_repeated_wording_and_an_extra_field_are_refused(tmp_path: Path) -> None:
    d = good()
    w = d["items"][0]["points"][0]["wordings"]
    w.append(list(w[0]))
    with pytest.raises(ValueError, match="twice"):
        load_with(tmp_path, d)
    d = good()
    d["items"][0]["grade"] = "A"
    with pytest.raises(ValueError):
        load_with(tmp_path, d)


def test_the_event_carries_the_marks_and_only_for_a_topic_with_an_item() -> None:
    ev = exam.event_for("physics_form5_force_and_elasticity")
    assert ev is not None and ev.marks == len(ev.points) == 3
    assert exam.event_for("physics_form5_nothing") is None
