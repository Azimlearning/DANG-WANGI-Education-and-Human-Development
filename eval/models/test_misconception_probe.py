"""The misconception probe set is well-formed: every positive names a real entry, every entry has positives and neutral questions, the set is balanced.
(The matcher's accuracy on it is a measurement, printed by misconception_eval.py and recorded in refdocs/evidence, not an assertion: it would pin a
number that a better matcher should be free to move.)"""

from __future__ import annotations

import json

from api.models.misconceptions import DATA
from eval.models.misconception_eval import PROBE, evaluate, load_items


def test_every_positive_names_a_real_entry_and_every_entry_has_probes() -> None:
    entries = {e["id"] for e in json.loads(DATA.read_text(encoding="utf-8"))["entries"]}
    items = load_items()
    positives = [i for i in items if i["kind"] == "positive"]
    assert {i["id"] for i in positives} == entries
    assert all(i["id"] is None for i in items if i["kind"] != "positive")
    for entry in entries:
        assert sum(1 for i in positives if i["id"] == entry) >= 4


def test_the_set_has_neutral_and_off_topic_questions_and_no_duplicates() -> None:
    items = load_items()
    kinds = {i["kind"] for i in items}
    assert kinds == {"positive", "neutral", "offtopic"}
    questions = [i["q"] for i in items]
    assert len(questions) == len(set(questions)) and PROBE.exists()


def test_the_evaluation_runs_and_its_numbers_are_proportions() -> None:
    r = evaluate(1.0)
    assert 0.0 <= r["recall"] <= 1.0 and 0.0 <= r["false_positive_rate"] <= 1.0
    assert r["positives"] + r["quiet_items"] == len(load_items())
