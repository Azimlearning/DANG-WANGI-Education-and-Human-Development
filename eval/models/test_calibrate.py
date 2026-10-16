"""The gate file and the model card are generated; a test fails if either is stale against the artifact and metrics."""

from __future__ import annotations

import json

from eval.models.calibrate import CARD, GATE, MIN_COVERAGE, TARGET, build, card


def test_gate_and_model_card_are_up_to_date() -> None:
    gate, failures = build()
    assert GATE.read_text(encoding="utf-8") == json.dumps(gate, indent=2, sort_keys=True) + "\n", (
        "run eval/models/calibrate.py"
    )
    assert CARD.read_text(encoding="utf-8") == card(gate, failures), "run eval/models/calibrate.py"


def test_a_head_is_called_useful_only_if_it_reaches_the_target_with_enough_coverage() -> None:
    gate, _ = build()
    for head, g in gate["heads"].items():
        if g["useful"]:
            assert g["val_accuracy"] >= TARGET and g["val_coverage"] >= MIN_COVERAGE, head
        else:
            assert g["threshold"] is None


def test_the_card_states_its_limits() -> None:
    text = CARD.read_text(encoding="utf-8")
    for needle in ("LLM teacher", "agreement with that teacher", "Do not use it for", "Baseline", "stale"):
        assert needle.lower() in text.lower()
