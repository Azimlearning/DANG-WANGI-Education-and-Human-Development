"""The L6 set stays well formed (fast). The full run is `uv run python eval/l6/run.py`; it takes about a minute and a half."""

from __future__ import annotations

import re
from pathlib import Path

from api.kit import latest_version
from eval.l6.mutations import MUTATIONS

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "data" / "fixtures" / "envs"
KIT = REPO / "packages" / "kit" / "dist"

# Pinned: defects we believe the verifier cannot see. Closing one is good news and means removing it here AND from the mutation.
KNOWN_MISSES = {
    "kit-hookes-narrow-spike",
    "page-wrong-label",
    "page-false-prose",
    "g-timer-60s-forge",
    "g-coarse-pointer-forge",
    "drag-overlay-pointer-transparent",
}


def test_ids_are_unique_and_expectations_are_known() -> None:
    ids = [m.id for m in MUTATIONS]
    assert len(ids) == len(set(ids))
    assert {m.expect for m in MUTATIONS} <= {"refuse", "accept", "neutralise"}


def test_every_page_edit_applies_to_its_fixture() -> None:
    for m in MUTATIONS:
        html = (FIXTURES / m.base).read_text(encoding="utf-8")
        edited = m.edit(html)  # raises when the anchor is gone
        if m.edit is not MUTATIONS[0].edit and m.klass != "neutral":
            assert m.kit_edit or edited != html, m.id


def test_every_kit_edit_anchor_exists_in_the_built_bundle() -> None:
    core = (KIT / latest_version(KIT) / "core.js").read_text(encoding="utf-8")
    for m in MUTATIONS:
        if m.kit_edit:
            assert re.search(m.kit_edit[0], core), m.id


def test_the_known_misses_are_exactly_the_pinned_set() -> None:
    assert {m.id for m in MUTATIONS if m.known_miss} == KNOWN_MISSES


def test_the_set_has_neutral_controls_and_every_class() -> None:
    classes = {m.klass for m in MUTATIONS}
    assert {"physics", "provenance", "trust", "structure", "neutral"} <= classes
    assert sum(m.expect == "accept" for m in MUTATIONS) >= 6
