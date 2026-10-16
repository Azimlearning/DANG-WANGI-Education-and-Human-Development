"""Regression tests for the attack pages kit-guardian built against the P1 verifier, plus the Kit's runtime self-check in a real browser.

Each page was minted as `model-checked` before the fixes. The full set runs in `eval/l6/run.py`; these assert the specific outcomes and
prove the two defences that only a real browser can show: frozen built-ins, and the self-check hiding a forged Environment for a student.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api import postprocess
from api.verify.render import render_check
from eval.l6.mutations import MUTATIONS, SPRING
from eval.l6.run import KIT_DIST, ORIGIN, run_one

BY_ID = {m.id: m for m in MUTATIONS}
REFUSED = {
    "g-fullwidth-digits": "unowned_number",
    "g-list-marker-copy": "unbacked_copy_number",
    "g-newline-copy": "unbacked_copy_number",
    "g-step-context-copy": "unbacked_copy_number",
    "g-readout-label-mutation": "owned_changed",
    "g-note-mutation": "owned_changed",
    "g-patch-flatmap": "owned_changed",
    "g-ol-start": "forbidden_markup",
    "g-aria-valuenow": "unowned_attribute_number",
    "g-canvas-concat": "forbidden_markup",
    "g-input-unit-kg": "wrong_input_unit",
    "g-constant-readout-extra": "constant_readout",
}


@pytest.mark.parametrize("mutation_id", sorted(REFUSED))
def test_the_guardians_attack_is_refused_by_the_named_rule(mutation_id: str, tmp_path: Path) -> None:
    outcome = run_one(BY_ID[mutation_id], tmp_path)
    assert outcome.refused and outcome.rule == REFUSED[mutation_id], (outcome.stage, outcome.rule, outcome.reason)


def test_patching_a_built_in_before_adding_a_number_still_gets_the_number_caught(tmp_path: Path) -> None:
    outcome = run_one(BY_ID["g-patch-regexp"], tmp_path)
    assert outcome.refused and outcome.rule == "unowned_number"


def test_a_page_cannot_replace_methods_on_an_observable_or_a_built_in(tmp_path: Path) -> None:
    """The assignments are silently ignored (sloppy mode) because the Kit froze the intrinsics; the page then behaves normally."""
    assert not run_one(BY_ID["g-patch-observable-get"], tmp_path).refused


def _student_run(html: str, seconds: float) -> object:
    processed = postprocess.run(html, public_origin=ORIGIN, kit_version="0.1.0")
    assert isinstance(processed, str)
    return render_check(
        processed,
        kit_dist=KIT_DIST,
        public_origin=ORIGIN,
        interaction_seconds=seconds,
        plan_models=[],
        kit_lane=True,
        verify_mode=False,
    )


def test_runtime_self_check_reports_a_late_forgery_in_a_students_browser() -> None:
    """A readout overwritten 2.2 s after load (one second after load) is reported by the Kit itself."""
    html = BY_ID["g-timer-60s-forge"].edit(
        (Path(__file__).resolve().parents[2] / "data/fixtures/envs" / SPRING).read_text()
    )
    html = html.replace("60000", "1000")
    report = _student_run(html, 5.0)
    assert report.violations, "the Kit's self-check never reported the forged readout"  # type: ignore[attr-defined]
    assert "readout" in report.violations[0]  # type: ignore[attr-defined]


def test_runtime_self_check_leaves_an_honest_page_alone() -> None:
    html = (Path(__file__).resolve().parents[2] / "data/fixtures/envs" / SPRING).read_text()
    report = _student_run(html, 2.5)
    assert report.violations == []  # type: ignore[attr-defined]
