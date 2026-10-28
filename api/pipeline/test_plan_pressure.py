"""W15: the pressure tank. The Plan's scene, its checks (PLAN-019 for a scene drawn from a model's output), the assembler, and the verifier's grounding of the scene (D-65)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.pipeline.plan_checks import check, needed_components
from api.verify.provenance import widget_problems

REPO = Path(__file__).resolve().parents[2]
PRESSURE = json.loads((REPO / "data/plans/physics-f5-pressure_depth.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def changed(edit) -> dict:  # noqa: ANN001
    data = json.loads(json.dumps(PRESSURE))
    edit(data)
    return data


def codes(data: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in check(plan_module.Plan.model_validate(data), manifest)]


def test_the_pressure_lab_passes_every_check_and_draws_its_tank(manifest: kitmanifest.Manifest) -> None:
    plan = plan_module.Plan.model_validate(PRESSURE)
    assert plan.scene is not None and plan.scene.kind == "pressure" and plan.scene.source == "water"
    assert check(plan, manifest) == []
    assert "pressureScene" in needed_components(plan)
    page = assemble(plan, manifest).html
    assert "Synapse.pressureScene(env, { pressure: m_water, full: 200000.0 });" in page


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["scene"].update(source="depth"),  # a control, not the model's output
        lambda d: d["scene"].update(full=50000),  # clipped: the model reaches 196 200 Pa
        lambda d: d["scene"].update(full=900000),  # mostly unused
    ],
)
def test_PLAN_019_a_pressure_tank_draws_the_pressure_model_at_a_fitting_scale(manifest: kitmanifest.Manifest, edit) -> None:  # noqa: ANN001
    assert "PLAN-019" in codes(changed(edit), manifest)


def test_the_verifier_grounds_the_tank_on_the_pressure_model() -> None:
    def audit(model: str, full: float) -> dict:
        chain = {"kind": "model", "id": model, "params": {"density": 1000, "g": 9.81}, "inputs": {"depth": {"kind": "control", "id": "depth"}}}
        return {
            "widgets": [{"kind": "scene", "id": "pressure", "full": full, "chain": chain, "problems": [], "exact": [], "layout": []}],
            "controls": [{"id": "depth", "unit": "m", "min": 0, "max": 20, "grid": 20}],
            "constants": [],
        }

    assert widget_problems(audit("fluids.pressure_depth", 200000)) == []
    assert any(p.rule == "scene_ungrounded" for p in widget_problems(audit("mechanics.hookes", 200000)))
    assert any(p.rule == "scene_scale" for p in widget_problems(audit("fluids.pressure_depth", 50000)))
