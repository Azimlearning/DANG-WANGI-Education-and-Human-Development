"""W4: a control operated by dragging masses, and a scene that draws a model's output. The Plan fields, their checks (PLAN-018, PLAN-019), the assembler, and the guarantee that a
Plan that does not use them is assembled exactly as before."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import SKELETON_PARTS, assemble, present_parts
from api.pipeline.plan_checks import check, needed_components

REPO = Path(__file__).resolve().parents[2]
HOOKE = json.loads((REPO / "data/plans/physics-f5-hookes_amali.json").read_text(encoding="utf-8"))
OHM = json.loads((REPO / "data/plans/physics-f5-ohm_explorer.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def plan_of(data: dict) -> plan_module.Plan:
    return plan_module.Plan.model_validate(data)


def with_control(**changes: object) -> dict:
    data = json.loads(json.dumps(HOOKE))
    data["controls"][0].update(changes)
    return data


def codes(data: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in check(plan_of(data), manifest)]


def test_the_hooke_bench_is_a_mass_hanger_and_a_spring_scene_and_passes_every_check(manifest: kitmanifest.Manifest) -> None:
    plan = plan_of(HOOKE)
    assert plan.controls[0].surface == "masses" and plan.controls[0].grid == 5
    assert plan.scene is not None and plan.scene.kind == "spring" and plan.scene.source == "spring"
    assert check(plan, manifest) == []
    assert {"massHanger", "springScene"} <= needed_components(plan)


def test_a_plan_without_the_new_fields_is_exactly_what_it_was(manifest: kitmanifest.Manifest) -> None:
    plan = plan_of(OHM)
    assert plan.controls[0].surface == "slider" and plan.scene is None
    assert not {"massHanger", "springScene"} & needed_components(plan)
    assert not {"scene"} & present_parts(plan)
    page = assemble(plan, manifest).html
    assert "Synapse.slider(" in page and "Synapse.massHanger" not in page and "Synapse.springScene" not in page


def test_the_assembler_writes_the_mass_hanger_and_the_scene_from_the_plan_and_nothing_else(manifest: kitmanifest.Manifest) -> None:
    page = assemble(plan_of(HOOKE), manifest).html
    assert 'Synapse.massHanger(env, {"id": "load"' in page and '"grid": 5' in page and "Synapse.slider(" not in page
    assert "Synapse.springScene(env, { extension: m_spring, full: 0.25 });" in page
    assert page.index("Synapse.readout(") < page.index("Synapse.springScene(")  # after the model it draws
    assert "scene" in SKELETON_PARTS["virtual_experiment"] and "scene" in SKELETON_PARTS["simulation"]


@pytest.mark.parametrize("grid", [1, 9, 40])
def test_PLAN_018_the_number_of_masses_is_two_to_eight(manifest: kitmanifest.Manifest, grid: int) -> None:
    assert "PLAN-018" in codes(with_control(grid=grid), manifest)  # other checks may also object: the Plan's sentences name positions the new grid lacks


@pytest.mark.parametrize("value", [1, 3.3, 9.9])
def test_PLAN_018_the_starting_value_is_a_whole_number_of_masses(manifest: kitmanifest.Manifest, value: float) -> None:
    assert codes(with_control(value=value), manifest) == ["PLAN-018"]


def test_PLAN_018_does_not_apply_to_a_slider_and_accepts_every_whole_number_of_masses(manifest: kitmanifest.Manifest) -> None:
    assert codes(with_control(surface="slider", grid=10, value=3), manifest) == []
    for n in range(0, 6):
        assert codes(with_control(value=2 * n), manifest) == []


def test_PLAN_019_a_scene_must_draw_a_model_it_is_registered_for(manifest: kitmanifest.Manifest) -> None:
    missing = json.loads(json.dumps(HOOKE))
    missing["scene"]["source"] = "nothing"
    assert codes(missing, manifest) == ["PLAN-019"]
    wrong = json.loads(json.dumps(OHM))
    wrong["scene"] = {"kind": "spring", "source": wrong["models"][0]["id"], "full": 1.0}
    assert "PLAN-019" in codes(wrong, manifest)


@pytest.mark.parametrize("bad", [{"surface": "knob"}, {"surface": 1}])
def test_a_control_surface_must_be_one_of_the_known_ones(bad: dict) -> None:
    with pytest.raises(ValidationError):
        plan_of(with_control(**bad))


@pytest.mark.parametrize("full", [0, -1, float("inf"), float("nan"), "0.25"])
def test_a_scene_scale_must_be_a_positive_finite_number(full: object) -> None:
    data = json.loads(json.dumps(HOOKE))
    data["scene"]["full"] = full
    with pytest.raises(ValidationError):
        plan_module.Plan.model_validate(data)


def test_the_scene_has_no_other_fields_and_only_the_one_kind() -> None:
    for extra in ({"label": "x"}, {"kind": "orbit"}):
        data = json.loads(json.dumps(HOOKE))
        data["scene"].update(extra)
        with pytest.raises(ValidationError):
            plan_module.Plan.model_validate(data)


def test_the_planner_schema_describes_both_new_fields() -> None:
    schema = json.loads((REPO / "api/prompts/schemas/plan.schema.json").read_text(encoding="utf-8"))
    assert schema == plan_module.json_schema()
    assert "scene" in schema["properties"] and "surface" in schema["$defs"]["ControlSpec"]["properties"]


@pytest.mark.parametrize("full", [0.1, 0.19, 0.5, 1.0, 40.0])
def test_PLAN_019_the_drawing_scale_must_fit_the_models_output_at_the_controls_maximum(manifest: kitmanifest.Manifest, full: float) -> None:
    """The spring reaches 0.2 m at 10 N: a scale from 0.2 to 0.4 draws it nearly full and never clipped."""
    data = json.loads(json.dumps(HOOKE))
    data["scene"]["full"] = full
    assert codes(data, manifest) == ["PLAN-019"]


@pytest.mark.parametrize("full", [0.2, 0.25, 0.4])
def test_PLAN_019_accepts_a_scale_from_the_peak_to_twice_the_peak(manifest: kitmanifest.Manifest, full: float) -> None:
    data = json.loads(json.dumps(HOOKE))
    data["scene"]["full"] = full
    assert codes(data, manifest) == []
