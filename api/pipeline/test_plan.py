from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline import plan_checks as pc
from api.pipeline.plan import Plan

REPO = Path(__file__).resolve().parents[2]
GOLDEN = sorted((REPO / "data" / "plans").glob("*.json"))
SCHEMA = REPO / "api" / "prompts" / "schemas" / "plan.schema.json"


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def raw(name: str) -> dict:
    return json.loads((REPO / "data" / "plans" / f"physics-f5-{name}.json").read_text(encoding="utf-8"))


def codes(plan_dict: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in pc.check(Plan.model_validate(plan_dict), manifest)]


def with_(name: str, **changes: object) -> dict:
    d = raw(name)
    d.update(changes)
    return d


def test_there_is_a_golden_plan_for_each_physics_form_5_topic() -> None:
    assert {json.loads(p.read_text())["topic"] for p in GOLDEN if p.name.startswith("physics-f5-")} == {
        "physics_form5_force_and_elasticity",
        "physics_form5_electricity",
        "physics_form5_forces_and_pressure",
        "physics_form5_electromagnetism",
        "physics_form5_nuclear_physics",
    }


def refraction() -> dict:
    return json.loads((REPO / "data" / "plans" / "physics-f4-refraction.json").read_text(encoding="utf-8"))


def test_a_control_that_can_reach_a_models_ceiling_is_plan_005(manifest: kitmanifest.Manifest) -> None:
    """The angle of incidence must stay below 90 degrees: a control that can reach 90 or more is refused, one that stops short of it is accepted."""
    d = refraction()
    assert codes(d, manifest) == []
    d["controls"][0]["max"] = 90
    d["controls"][0]["grid"] = 9
    assert "PLAN-005" in codes(d, manifest)
    d["controls"][0]["max"] = 100
    d["controls"][0]["grid"] = 10
    assert "PLAN-005" in codes(d, manifest)
    d["controls"][0]["max"] = 85
    d["controls"][0]["grid"] = 17
    assert "PLAN-005" not in codes(d, manifest)


def test_a_constant_above_a_models_ceiling_is_plan_005(manifest: kitmanifest.Manifest) -> None:
    d = refraction()
    d["constants"] = [{"id": "angle", "label": "Angle", "unit": "deg", "value": 95}]
    d["models"][0]["inputs"]["incidence_angle"] = "angle"
    d["controls"] = [c for c in d["controls"] if c["id"] != "incidence"]
    d["graphs"] = []
    d["table"] = None
    d["steps"] = []
    assert "PLAN-005" in codes(d, manifest)


def test_the_manifest_carries_the_ceiling_the_checks_use(manifest: kitmanifest.Manifest) -> None:
    q = manifest.models["physics.refraction_angle"].inputs["incidence_angle"]
    assert q.min == 0 and q.max == 90 and q.max_exclusive
    assert manifest.models["physics.refraction_angle"].inputs["refractive_index"].max is None


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.stem)
def test_each_golden_plan_passes_the_plan_checks(path: Path, manifest: kitmanifest.Manifest) -> None:
    plan = plan_module.parse(path.read_text(encoding="utf-8"))
    assert pc.check(plan, manifest) == []


def test_the_manifest_gives_the_domain_the_checks_use(manifest: kitmanifest.Manifest) -> None:
    hookes = manifest.models["mechanics.hookes"]
    assert hookes.params["k"].exclusive and hookes.inputs["load"].unit == "N" and hookes.output_unit == "m"


def test_unknown_model_is_plan_002(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["models"][0]["model"] = "mechanics.newton"
    assert "PLAN-002" in codes(d, manifest)


def test_k_equal_to_zero_is_outside_the_domain_plan_003(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["models"][0]["params"]["k"] = 0
    assert "PLAN-003" in codes(d, manifest)
    d["models"][0]["params"] = {"k": 50, "extra": 1}
    assert "PLAN-003" in codes(d, manifest)


def test_a_control_in_the_wrong_unit_or_unbound_input_is_plan_004(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["controls"][0]["unit"] = "kg"
    assert "PLAN-004" in codes(d, manifest)
    d = raw("hookes_amali")
    d["models"][0]["inputs"] = {"load": "nothing"}
    assert "PLAN-004" in codes(d, manifest)


def test_a_range_below_the_domain_minimum_is_plan_005(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["controls"][0].update(min=-5, max=5, value=1)
    assert "PLAN-005" in codes(d, manifest)
    d = raw("ohm_explorer")
    d["controls"][1].update(min=0, value=4)  # resistance must be above 0
    assert "PLAN-005" in codes(d, manifest)


def test_a_readout_with_no_source_is_plan_006(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["readouts"][0]["source"] = "ghost"
    assert "PLAN-006" in codes(d, manifest)


def test_a_wrong_readout_unit_or_bad_conversion_is_plan_007(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["readouts"][0]["unit"] = "cm"
    assert "PLAN-007" in codes(d, manifest)
    d = raw("pressure_depth")
    d["readouts"][0]["convert_to"] = "kg"
    assert "PLAN-007" in codes(d, manifest)


def test_an_unbacked_number_in_a_sentence_is_plan_008(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["sentences"] = ["At 7 N the extension is 0.14 m."]
    assert "PLAN-008" in codes(d, manifest)
    d["sentences"] = ["At 4 N the extension is 0.08 m."]
    assert "PLAN-008" in codes(d, manifest)  # 0.08 is a computed result, never a sentence number


def test_a_missing_component_is_plan_009(manifest: kitmanifest.Manifest) -> None:
    fake = kitmanifest.Manifest(
        manifest.version,
        manifest.sha256,
        {k: v for k, v in manifest.components.items() if k != "graph"},
        manifest.models,
    )
    assert "PLAN-009" in [i.code for i in pc.check(plan_module.parse(json.dumps(raw("hookes_amali"))), fake)]


def test_oversize_copy_and_grid_are_plan_010(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["sentences"] = ["x" * 230] * 6
    assert "PLAN-010" in codes(d, manifest)


def test_duplicate_ids_are_plan_011(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["models"][0]["id"] = "load"
    assert "PLAN-011" in codes(d, manifest)


def test_a_virtual_experiment_without_its_parts_is_plan_012(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["experiment"] = None
    assert "PLAN-012" in codes(d, manifest)


def test_a_start_outside_the_range_is_plan_014_and_is_repaired(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["controls"][0]["value"] = 25
    plan = Plan.model_validate(d)
    issues = pc.check(plan, manifest)
    assert [i.code for i in issues] == ["PLAN-014"] and issues[0].repairable
    fixed = pc.repair(plan, issues)
    assert fixed.controls[0].value == 10 and pc.check(fixed, manifest) == []


def test_a_malformed_plan_is_refused_by_the_schema_plan_001() -> None:
    d = raw("hookes_amali")
    d["surprise"] = 1
    with pytest.raises(ValidationError) as err:
        Plan.model_validate(d)
    assert pc.issue_from_validation(err.value).code == "PLAN-001"
    d = raw("hookes_amali")
    d["controls"][0]["grid"] = "10"
    with pytest.raises(ValidationError):
        Plan.model_validate(d)
    with pytest.raises(ValidationError):
        plan_module.parse('{"id": "x"}')


def test_every_issue_has_a_hint_and_a_path(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    d["models"][0]["params"]["k"] = 0
    d["readouts"][0]["unit"] = "cm"
    for i in pc.check(Plan.model_validate(d), manifest):
        assert i.hint and i.path and i.message


def test_the_json_schema_file_matches_the_model() -> None:
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == plan_module.json_schema(), (
        "regenerate with: uv run python -m api.pipeline.plan"
    )


def test_a_dilution_that_can_go_below_its_starting_volume_is_plan_015(manifest: kitmanifest.Manifest) -> None:
    d = json.loads((REPO / "data" / "plans" / "chemistry-f4-dilution.json").read_text(encoding="utf-8"))
    assert codes(d, manifest) == []
    d["controls"][0]["min"] = 10
    d["controls"][0]["value"] = 50
    assert "PLAN-015" in codes(d, manifest)


def test_a_model_under_a_topic_it_is_not_registered_for_is_plan_016(manifest: kitmanifest.Manifest) -> None:
    d = raw("hookes_amali")
    assert codes(d, manifest) == []
    d["topic"] = "biology_form4_cell_biology"
    assert "PLAN-016" in codes(d, manifest)


def test_a_control_whose_effect_is_hidden_by_the_readout_digits_is_plan_017(manifest: kitmanifest.Manifest) -> None:
    d = json.loads((REPO / "data" / "plans" / "chemistry-f4-titration.json").read_text(encoding="utf-8"))
    assert codes(d, manifest) == []
    for r in d["readouts"]:
        r["digits"] = 0  # 0.1 mol/dm3 x 25 / vb shows as 0 across the whole range
    assert "PLAN-017" in codes(d, manifest)


def test_every_free_text_field_and_collection_in_a_plan_has_a_size_cap() -> None:
    base = raw("hookes_amali")

    def refused(**changes: object) -> bool:
        try:
            Plan.model_validate({**base, **changes})
        except ValidationError:
            return True
        return False

    assert refused(experiment_ref="x" * 5000)
    assert refused(citation_ids=["a" * 5000])
    assert refused(citation_ids=["a"] * 7)
    models = [{**base["models"][0], "model": "mechanics." + "a" * 5000}]
    assert refused(models=models)
    models = [{**base["models"][0], "params": {f"p{i}": 1.0 for i in range(9)}}]
    assert refused(models=models)
    models = [{**base["models"][0], "inputs": {f"i{i}": "load" for i in range(9)}}]
    assert refused(models=models)
    assert refused(title="t" * 5000) and refused(note="n" * 5000) and refused(goal="g" * 5000)
    assert refused(sentences=["s" * 5000]) and refused(steps=["s" * 5000]) and refused(sentences=["s"] * 7)


def test_every_plan_check_code_has_a_test_that_makes_it_fire() -> None:
    """A check with no test that triggers it could be deleted unnoticed. Each code must appear in an assertion in this file."""
    source = (Path(__file__).resolve().parent / "plan_checks.py").read_text(encoding="utf-8")
    emitted = set(__import__("re").findall(r'"(PLAN-\\d+)"', source))
    tests = Path(__file__).read_text(encoding="utf-8").upper().replace("_", "-")
    missing = sorted(
        code
        for code in emitted
        if f'"{code}"' not in tests and code.lower().replace("-", "") not in tests.lower().replace("-", "")
    )
    assert not missing, f"no test fires {missing}"


def half_life() -> dict:
    return json.loads((REPO / "data" / "plans" / "physics-f5-half_life.json").read_text(encoding="utf-8"))


def test_a_half_life_time_control_must_move_in_whole_half_lives_plan_021(manifest: kitmanifest.Manifest) -> None:
    """The book states the half-life rule for whole numbers of half-lives. The golden Plan runs 0 to 48 minutes in 8 steps of 6, one half-life each."""
    d = half_life()
    assert codes(d, manifest) == []
    d["controls"][0].update(grid=10)  # steps of 4.8 minutes: between half-lives
    assert "PLAN-021" in codes(d, manifest)
    d = half_life()
    d["controls"][0].update(min=3, max=51, grid=8)  # starts half way through a half-life
    assert "PLAN-021" in codes(d, manifest)
    d = half_life()
    d["controls"][0].update(grid=4)  # steps of 12: two half-lives at a time, still whole
    assert "PLAN-021" not in codes(d, manifest)
    d = half_life()
    d["models"][0]["params"]["half_life"] = 7  # a different half-life makes the same control wrong
    assert "PLAN-021" in codes(d, manifest)
