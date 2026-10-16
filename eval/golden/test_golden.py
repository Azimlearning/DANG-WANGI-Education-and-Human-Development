from __future__ import annotations

import asyncio
import json

from eval.golden.run import PIN, SET, load, route_all


def test_the_golden_set_is_pinned_by_hash_and_well_formed() -> None:
    questions = load()  # raises if the hash changed without a declared amendment
    assert len(questions) == 24 and len({q["id"] for q in questions}) == 24
    assert {q["expect_topic"] for q in questions} == {
        "physics_form5_force_and_elasticity",
        "physics_form5_electricity",
        "physics_form5_forces_and_pressure",
    }
    assert all(5 <= len(q["question"]) <= 200 for q in questions)
    assert len(PIN.read_text().strip()) == 64 and "declared amendment" in json.loads(SET.read_text())["note"]


def test_the_local_router_alone_does_not_get_worse_on_the_golden_set() -> None:
    """A regression floor, not a target: 17 of 24 at the time of writing (7 wrongly `none`, which the router sends to the fallback)."""
    routed = asyncio.run(route_all(load()))
    assert sum(r["expect"] == r["got"] for r in routed) >= 17


def test_the_breadth_set_is_pinned_and_covers_each_new_topic_twice() -> None:
    questions = load("breadth")
    topics = {q["expect_topic"] for q in questions}
    assert len(questions) == 14 and len(topics) == 7
    assert all(sum(q["expect_topic"] == t for q in questions) == 2 for t in topics)
