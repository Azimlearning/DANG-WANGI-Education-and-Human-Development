"""W15: the refraction scene. The Plan fields, their checks (PLAN-019 for a refraction scene), the assembler, and the verifier's grounding of the scene (D-65)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.pipeline.plan_checks import check, needed_components
from api.verify.provenance import widget_problems

REPO = Path(__file__).resolve().parents[2]
REFRACTION = json.loads((REPO / "data/plans/physics-f4-refraction.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def plan_of(data: dict) -> plan_module.Plan:
    return plan_module.Plan.model_validate(data)


def changed(edit) -> dict:  # noqa: ANN001
    data = json.loads(json.dumps(REFRACTION))
    edit(data)
    return data


def codes(data: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in check(plan_of(data), manifest)]


def test_the_refraction_lab_passes_every_check_and_needs_the_scene(manifest: kitmanifest.Manifest) -> None:
    plan = plan_of(REFRACTION)
    assert plan.scene is not None and plan.scene.kind == "refraction" and plan.scene.source == "incidence" and plan.scene.model == "bend"
    assert check(plan, manifest) == []
    assert "refractionScene" in needed_components(plan)
    assert "refractionScene" in manifest.components


def test_the_assembler_writes_the_model_before_the_scene(manifest: kitmanifest.Manifest) -> None:
    page = assemble(plan_of(REFRACTION), manifest).html
    assert "Synapse.refractionScene(env, { incidence: c_incidence, refraction: m_bend });" in page
    assert page.index("Synapse.refractionAngle(") < page.index("Synapse.refractionScene(")


def test_a_refraction_scene_needs_a_model() -> None:
    with pytest.raises(ValidationError):
        plan_of(changed(lambda d: d["scene"].pop("model")))


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["scene"].update(source="index"),  # a control, not in degrees
        lambda d: d["scene"].update(source="nothing"),  # not a control
        lambda d: d["scene"].update(model="limit"),  # the critical angle, not the angle of refraction
        lambda d: d["scene"].update(full=60),  # not the whole range of an angle
        lambda d: d["controls"][0].update(max=120, value=40),  # an angle of incidence past 90 degrees
    ],
)
def test_PLAN_019_a_refraction_scene_must_draw_the_angles_it_claims(manifest: kitmanifest.Manifest, edit) -> None:  # noqa: ANN001
    assert "PLAN-019" in codes(changed(edit), manifest)


def test_the_angle_of_refraction_must_be_fed_by_the_control_the_scene_draws(manifest: kitmanifest.Manifest) -> None:
    def rebind(d: dict) -> None:
        d["controls"].append({"id": "other", "label": "Another angle", "unit": "deg", "min": 0, "max": 60, "value": 10, "grid": 6})
        d["models"][0]["inputs"]["incidence_angle"] = "other"

    assert "PLAN-019" in codes(changed(rebind), manifest)


def _audit(full: object = 90.0, unit: str = "deg", fed: str = "incidence", lo: float = 0, hi: float = 80) -> dict:
    """A minimal audit of a page with one refraction scene, for the verifier's grounding rules alone."""
    chain = {"kind": "model", "id": "physics.refraction_angle", "params": {}, "inputs": {"incidence_angle": {"kind": "control", "id": fed}, "refractive_index": {"kind": "control", "id": "index"}}}
    return {
        "widgets": [{"kind": "scene", "id": "refraction", "full": full, "chain": chain, "sourceChain": {"kind": "control", "id": "incidence"}, "problems": [], "exact": [], "layout": []}],
        "controls": [
            {"id": "incidence", "unit": unit, "min": lo, "max": hi, "grid": 8},
            {"id": "index", "unit": "ratio", "min": 1, "max": 2.5, "grid": 6},
            {"id": "other", "unit": "deg", "min": 0, "max": 60, "grid": 6},
        ],
        "constants": [],
    }


def test_the_verifier_grounds_a_refraction_scene_on_the_control_it_draws() -> None:
    assert widget_problems(_audit()) == []
    for audit in (_audit(unit="ratio"), _audit(fed="other"), _audit(full=60.0), _audit(hi=120)):
        found = widget_problems(audit)
        assert any(p.rule in ("scene_ungrounded", "scene_scale") for p in found), found
