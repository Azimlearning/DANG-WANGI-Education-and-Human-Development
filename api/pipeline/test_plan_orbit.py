"""W4 stage 4: Newton's cannonball. The Plan fields, their checks (PLAN-019 for an orbit scene), the assembler, and the independent references of the three models it rests on."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.pipeline.plan_checks import check, needed_components
from api.verify.provenance import orbit_outcome
from api.verify.references import evaluate_model

REPO = Path(__file__).resolve().parents[2]
ORBIT = json.loads((REPO / "data/plans/physics-f4-orbit.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def plan_of(data: dict) -> plan_module.Plan:
    return plan_module.Plan.model_validate(data)


def changed(edit) -> dict:  # noqa: ANN001
    data = json.loads(json.dumps(ORBIT))
    edit(data)
    return data


def codes(data: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in check(plan_of(data), manifest)]


def test_the_cannonball_bench_passes_every_check_and_needs_the_scene_and_the_three_models(manifest: kitmanifest.Manifest) -> None:
    plan = plan_of(ORBIT)
    assert plan.scene is not None and plan.scene.kind == "orbit" and plan.scene.model == "circular" and plan.scene.escape == "escape"
    assert check(plan, manifest) == []
    assert {"orbitScene", "circularSpeed", "escapeSpeed", "centripetalAcceleration"} <= needed_components(plan) | {manifest.models[m.model].export_name for m in plan.models}


def test_the_assembler_writes_the_models_before_the_scene(manifest: kitmanifest.Manifest) -> None:
    page = assemble(plan_of(ORBIT), manifest).html
    assert "Synapse.orbitScene(env, { speed: c_launch, circular: m_circular, escape: m_escape, full: 15.0 });" in page
    assert page.index("Synapse.escapeSpeed(") < page.index("Synapse.orbitScene(")
    assert page.index("Synapse.circularSpeed(") < page.index("Synapse.orbitScene(")


def test_an_orbit_scene_needs_a_model_and_an_escape_and_no_other_scene_has_an_escape() -> None:
    with pytest.raises(ValidationError):
        plan_of(changed(lambda d: d["scene"].pop("escape")))
    with pytest.raises(ValidationError):
        plan_of(changed(lambda d: d["scene"].pop("model")))
    ferm = json.loads((REPO / "data/plans/biology-f4-fermentation.json").read_text(encoding="utf-8"))
    ferm["scene"]["escape"] = "ferment"
    with pytest.raises(ValidationError):
        plan_module.Plan.model_validate(ferm)


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["scene"].update(source="nothing"),
        lambda d: d["scene"].update(source="circular"),  # a model, not a control
        lambda d: d["controls"][0].update(unit="m/s"),
        lambda d: d["scene"].update(model="nothing"),
        lambda d: d["scene"].update(model="escape"),  # swapped
        lambda d: d["scene"].update(escape="circular"),
        lambda d: d["scene"].update(full=14),
        lambda d: d["scene"].update(full=400),
        lambda d: d["constants"][0].update(value=1737),  # the Moon's radius
        lambda d: d["constants"][0].update(unit="m"),
        lambda d: [m["params"].update(central_mass=6.4e23) for m in d["models"][:2]],
        lambda d: d["models"][1]["params"].update(central_mass=5.97e24),  # two different masses
        lambda d: d["controls"][0].update(min=8.5, value=9),  # never falls back or circles
        lambda d: d["controls"][0].update(max=11),  # never escapes
        lambda d: d["controls"][0].update(grid=5, value=1),  # too coarse to show a circle
    ],
    ids=[
        "no-source",
        "source-is-a-model",
        "control-in-m-per-s",
        "no-model",
        "models-swapped",
        "escape-is-circular",
        "capacity-too-small",
        "capacity-huge",
        "moon-radius",
        "radius-in-metres",
        "not-earths-mass",
        "two-masses",
        "never-falls-or-circles",
        "never-escapes",
        "too-coarse",
    ],
)
def test_PLAN_019_an_orbit_scene_must_fit_its_control_and_Earth(manifest: kitmanifest.Manifest, edit) -> None:  # noqa: ANN001
    found = codes(changed(edit), manifest)
    assert "PLAN-019" in found, found


def test_the_radius_must_be_one_declared_constant_for_both_speeds(manifest: kitmanifest.Manifest) -> None:
    def second_radius(d: dict) -> None:
        d["constants"].append({"id": "radius2", "label": "A second radius", "unit": "km", "value": 6371})
        d["models"][1]["inputs"]["radius"] = "radius2"

    assert "PLAN-019" in codes(changed(second_radius), manifest)


def test_the_four_outcomes_use_one_rule_with_a_two_percent_circle() -> None:
    c, e = 7.9095, 11.1857
    assert [orbit_outcome(v, c, e) for v in (3, 7.9, 9.5, 11.1857, 14)] == ["falls", "circle", "oval", "escapes", "escapes"]
    assert orbit_outcome(c * 0.97, c, e) == "falls" and orbit_outcome(c * 1.03, c, e) == "oval"


def test_the_references_give_the_textbook_numbers_and_the_escape_speed_is_root_two_times_the_circular() -> None:
    mass = {"central_mass": 5.972e24}
    c = evaluate_model("physics.circular_speed", mass, {"radius": 6371})
    e = evaluate_model("physics.escape_speed", mass, {"radius": 6371})
    assert c == pytest.approx(7.91, abs=0.01) and e == pytest.approx(11.19, abs=0.01) and e / c == pytest.approx(math.sqrt(2))
    a = evaluate_model("physics.centripetal_acceleration", {}, {"speed": c, "radius": 6371})
    assert a == pytest.approx(5.972e24 * 6.674e-11 / (6371e3) ** 2, rel=1e-6)  # the pull of gravity at that radius


@pytest.mark.parametrize(
    ("model", "params", "inputs"),
    [
        ("physics.circular_speed", {"central_mass": 5.972e24}, {"radius": 0}),
        ("physics.circular_speed", {"central_mass": 0}, {"radius": 6371}),
        ("physics.escape_speed", {"central_mass": 5.972e24}, {"radius": -1}),
        ("physics.centripetal_acceleration", {}, {"speed": -1, "radius": 6371}),
        ("physics.centripetal_acceleration", {}, {"speed": 1, "radius": 0}),
        ("physics.circular_speed", {"central_mass": 5.972e24}, {"radius": math.nan}),
    ],
)
def test_the_references_refuse_values_outside_their_domain(model: str, params: dict, inputs: dict) -> None:
    with pytest.raises(ValueError):
        evaluate_model(model, params, inputs)
