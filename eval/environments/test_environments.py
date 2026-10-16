from __future__ import annotations

import json
from collections import Counter

from eval.environments.build import PLANS, REPORT


def test_there_are_at_least_three_environments_for_each_subject() -> None:
    subjects = Counter(json.loads(p.read_text())["topic"].split("_")[0] for p in PLANS.glob("*.json"))
    assert subjects["physics"] >= 3 and subjects["biology"] >= 3 and subjects["chemistry"] >= 3, subjects


def test_the_generated_report_lists_every_plan_and_says_what_it_does_not_show() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for path in PLANS.glob("*.json"):
        assert json.loads(path.read_text())["title"] in text, path.name
    assert "does and does not show" in text and "UNVERIFIED" in text
