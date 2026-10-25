"""W4 stage 2: a control operated by a stopcock, a titration scene, and the end-point model they rest on. The Plan fields, their checks (PLAN-018 for a valve, PLAN-019 for a titration
scene), the assembler, the independent reference, and the guarantee that the Hooke bench still assembles as before."""

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
from api.verify.references import evaluate_model

REPO = Path(__file__).resolve().parents[2]
TITR = json.loads((REPO / "data/plans/chemistry-f4-titration.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def plan_of(data: dict) -> plan_module.Plan:
    return plan_module.Plan.model_validate(data)


def changed(edit) -> dict:  # noqa: ANN001
    data = json.loads(json.dumps(TITR))
    edit(data)
    return data


def codes(data: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in check(plan_of(data), manifest)]


def test_the_titration_bench_is_a_valve_and_a_titration_scene_and_passes_every_check(manifest: kitmanifest.Manifest) -> None:
    plan = plan_of(TITR)
    assert plan.controls[0].surface == "valve" and plan.controls[0].grid == 7
    assert plan.scene is not None and plan.scene.kind == "titration" and plan.scene.source == "vb" and plan.scene.endpoint == "endpoint"
    assert check(plan, manifest) == []
    assert {"valve", "titrationScene", "titrationEndpoint"} <= needed_components(plan) | {manifest.models["chemistry.titration_endpoint_volume"].export_name}


def test_the_assembler_writes_the_valve_the_end_point_model_and_the_scene_after_the_model(manifest: kitmanifest.Manifest) -> None:
    page = assemble(plan_of(TITR), manifest).html
    assert 'Synapse.valve(env, {"id": "vb"' in page and "Synapse.slider(" not in page
    assert "Synapse.titrationEndpoint({" in page
    assert "Synapse.titrationScene(env, { added: c_vb, endpoint: m_endpoint, full: 50.0 });" in page
    assert page.index("Synapse.titrationEndpoint(") < page.index("Synapse.titrationScene(")


def test_PLAN_018_a_valve_has_two_to_forty_steps(manifest: kitmanifest.Manifest) -> None:
    assert "PLAN-018" in codes(changed(lambda d: d["controls"][0].update(grid=1)), manifest)
    for grid in (41, 100):  # the Plan's own limit on any control's grid is 40, which is also a valve's
        with pytest.raises(ValidationError):
            plan_of(changed(lambda d, g=grid: d["controls"][0].update(grid=g)))


@pytest.mark.parametrize("value", [6, 12.5, 39])
def test_PLAN_018_a_valve_starts_on_a_step(manifest: kitmanifest.Manifest, value: float) -> None:
    assert "PLAN-018" in codes(changed(lambda d: d["controls"][0].update(value=value)), manifest)


def test_PLAN_018_accepts_every_step_of_a_valve(manifest: kitmanifest.Manifest) -> None:
    for n in range(0, 8):
        assert "PLAN-018" not in codes(changed(lambda d, n=n: d["controls"][0].update(value=5 + 5 * n)), manifest)


@pytest.mark.parametrize("surface", ["tap", 1])
def test_a_control_surface_must_be_a_known_one(surface: object) -> None:
    with pytest.raises(ValidationError):
        plan_of(changed(lambda d: d["controls"][0].update(surface=surface)))


def test_a_titration_scene_needs_an_endpoint_and_no_other_scene_has_one() -> None:
    with pytest.raises(ValidationError):
        plan_of(changed(lambda d: d["scene"].pop("endpoint")))
    hooke = json.loads((REPO / "data/plans/physics-f5-hookes_amali.json").read_text(encoding="utf-8"))
    hooke["scene"]["endpoint"] = "spring"
    with pytest.raises(ValidationError):
        plan_module.Plan.model_validate(hooke)


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["scene"].update(source="nothing"),
        lambda d: d["scene"].update(source="endpoint"),  # a model, not a control
        lambda d: d["controls"][0].update(unit="mL"),
        lambda d: d["scene"].update(endpoint="nothing"),
        lambda d: d["scene"].update(endpoint="alkali"),  # the concentration model, not the end-point model
        lambda d: d["scene"].update(full=30),  # the control runs in 40
        lambda d: d["scene"].update(full=500),
        lambda d: d["constants"][1].update(value=0.02),  # the end point would be 125 cm3, which the control never reaches
        lambda d: d["constants"][1].update(value=1.0),  # 2.5 cm3, below the control's lowest position
    ],
    ids=["no-source", "source-is-a-model", "control-in-ml", "no-endpoint", "wrong-model", "capacity-too-small", "capacity-huge", "endpoint-unreachable-high", "endpoint-unreachable-low"],
)
def test_PLAN_019_a_titration_scene_must_fit_its_control_and_its_end_point_model(manifest: kitmanifest.Manifest, edit) -> None:  # noqa: ANN001
    assert "PLAN-019" in codes(changed(edit), manifest)


def test_the_end_point_reference_is_independent_and_agrees_with_the_concentration_model() -> None:
    """25 cm3 of 0.1 mol/dm3 acid against 0.125 mol/dm3 alkali needs 20 cm3; and 20 cm3 of that alkali gives back 0.125 mol/dm3 (the two references are each other's inverse)."""
    ve = evaluate_model("chemistry.titration_endpoint_volume", {"ma": 0.1, "acid_coeff": 1, "base_coeff": 1}, {"va": 25, "mb": 0.125})
    assert ve == pytest.approx(20)
    mb = evaluate_model("chemistry.titration_concentration", {"ma": 0.1, "acid_coeff": 1, "base_coeff": 1}, {"va": 25, "vb": ve})
    assert mb == pytest.approx(0.125)
    with pytest.raises(ValueError):
        evaluate_model("chemistry.titration_endpoint_volume", {"ma": 0.1, "acid_coeff": 1, "base_coeff": 1}, {"va": 25, "mb": 0})


def test_the_planner_schema_describes_the_new_fields() -> None:
    schema = json.loads((REPO / "api/prompts/schemas/plan.schema.json").read_text(encoding="utf-8"))
    assert schema == plan_module.json_schema()
    assert "endpoint" in schema["$defs"]["SceneSpec"]["properties"]
    assert "valve" in json.dumps(schema["$defs"]["ControlSpec"]["properties"]["surface"])


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["models"][1]["inputs"].update(va="vb"),  # the end point follows the control: the flask would be pink from the first position
        lambda d: d["models"][1]["params"].update(ma=0.2),  # another acid strength than the concentration uses
        lambda d: d["models"][1]["params"].update(base_coeff=2),
        lambda d: d["constants"].append({"id": "va2", "label": "Other acid", "unit": "cm3", "value": 30}) or d["models"][1]["inputs"].update(va="va2"),
        lambda d: d["constants"][1].update(value=0.11),  # an end point at 22.7 cm3, which is not one of the stopcock's steps
    ],
    ids=["follows-the-control", "other-acid-strength", "other-coefficient", "other-acid-volume", "end-point-off-a-step"],
)
def test_PLAN_019_the_end_point_is_the_solutions_property_and_agrees_with_the_concentration(manifest: kitmanifest.Manifest, edit) -> None:  # noqa: ANN001
    assert "PLAN-019" in codes(changed(edit), manifest)


def test_the_titration_plan_carries_the_eye_level_citation_and_in_plain_words() -> None:
    assert "titr_eye_level" in TITR["citation_ids"]
    pointers = json.loads((REPO / "data/citations/pointers.json").read_text(encoding="utf-8"))["pointers"]
    assert pointers["titr_eye_level"]["models"] == ["chemistry.titration_endpoint_volume"]
    assert pointers["titr_eye_level"]["printed_page"] == 171
