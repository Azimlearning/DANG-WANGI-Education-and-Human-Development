"""W4 stage 3: a control turned like a knob, a fermentation scene, and the respiration-energy model they rest on. The Plan fields, their checks (PLAN-018 for a dial, PLAN-019 for a
fermentation scene), the assembler, and the independent reference."""

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
FERM = json.loads((REPO / "data/plans/biology-f4-fermentation.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def plan_of(data: dict) -> plan_module.Plan:
    return plan_module.Plan.model_validate(data)


def changed(edit) -> dict:  # noqa: ANN001
    data = json.loads(json.dumps(FERM))
    edit(data)
    return data


def codes(data: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in check(plan_of(data), manifest)]


def test_the_fermentation_bench_takes_glucose_by_the_spoon_on_a_fermentation_scene_and_passes_every_check(manifest: kitmanifest.Manifest) -> None:
    plan = plan_of(FERM)
    assert plan.controls[0].surface != "dial" and plan.controls[0].grid == 8  # the dial gave way to spoons dropped on a beaker (2026-10-29)
    assert plan.scene is not None and plan.scene.kind == "fermentation" and plan.scene.source == "glucose" and plan.scene.model == "ferment"
    assert check(plan, manifest) == []
    assert "fermentationScene" in needed_components(plan) and "dial" not in needed_components(plan)


def test_the_assembler_writes_the_control_both_energy_models_and_the_scene_after_them(manifest: kitmanifest.Manifest) -> None:
    page = assemble(plan_of(FERM), manifest).html
    assert 'Synapse.slider(env, {"id": "glucose"' in page and "Synapse.dial(" not in page
    assert page.count("Synapse.respirationEnergy({") == 2
    assert "Synapse.fermentationScene(env, { fermented: c_glucose, energy: m_ferment, full: 0.004 });" in page
    assert page.index("Synapse.respirationEnergy(") < page.index("Synapse.fermentationScene(")


def test_PLAN_018_a_dial_has_two_to_forty_steps_and_starts_on_one(manifest: kitmanifest.Manifest) -> None:
    assert "PLAN-018" in codes(changed(lambda d: d["controls"][0].update(surface="dial", grid=1)), manifest)
    for value in (0.0003, 0.00075, 0.0012):
        assert "PLAN-018" in codes(changed(lambda d, v=value: d["controls"][0].update(surface="dial", value=v)), manifest)
    for n in range(0, 9):
        assert "PLAN-018" not in codes(changed(lambda d, n=n: d["controls"][0].update(surface="dial", value=0.0005 * n)), manifest)


def test_a_fermentation_scene_needs_a_model_and_no_other_scene_has_one() -> None:
    with pytest.raises(ValidationError):
        plan_of(changed(lambda d: d["scene"].pop("model")))
    hooke = json.loads((REPO / "data/plans/physics-f5-hookes_amali.json").read_text(encoding="utf-8"))
    hooke["scene"]["model"] = "spring"
    with pytest.raises(ValidationError):
        plan_module.Plan.model_validate(hooke)
    with pytest.raises(ValidationError):
        plan_of(changed(lambda d: d["scene"].update(endpoint="ferment")))


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["scene"].update(source="nothing"),
        lambda d: d["scene"].update(source="ferment"),  # a model, not a control
        lambda d: d["controls"][0].update(unit="g"),
        lambda d: d["scene"].update(model="nothing"),
        lambda d: d["models"][0]["inputs"].update(glucose="other") or d["controls"].append({"id": "other", "label": "Another amount", "unit": "mol", "min": 0, "max": 0.004, "value": 0.001, "grid": 8}),
        lambda d: d["scene"].update(full=0.003),
        lambda d: d["scene"].update(full=0.5),
    ],
    ids=["no-source", "source-is-a-model", "control-in-g", "no-model", "energy-of-another-control", "capacity-too-small", "capacity-huge"],
)
def test_PLAN_019_a_fermentation_scene_must_fit_its_control_and_its_own_energy(manifest: kitmanifest.Manifest, edit) -> None:  # noqa: ANN001
    assert "PLAN-019" in codes(changed(edit), manifest)


def test_the_energy_reference_is_independent_and_matches_the_textbook_figures() -> None:
    """One mole of glucose: 210 kJ by alcohol fermentation, 150 kJ by lactic acid fermentation, 2898 kJ by aerobic respiration (Table 7.1)."""
    for per_mole in (210, 150, 2898):
        assert evaluate_model("biology.respiration_energy", {"energy_per_mole": per_mole}, {"glucose": 1}) == pytest.approx(per_mole)
    assert evaluate_model("biology.respiration_energy", {"energy_per_mole": 210}, {"glucose": 0.004}) == pytest.approx(0.84)
    with pytest.raises(ValueError):
        evaluate_model("biology.respiration_energy", {"energy_per_mole": 0}, {"glucose": 1})
    with pytest.raises(ValueError):
        evaluate_model("biology.respiration_energy", {"energy_per_mole": 210}, {"glucose": -1})


def test_the_plan_cites_the_two_textbook_pages_and_the_pointers_say_what_they_support() -> None:
    assert FERM["citation_ids"] == ["ferment_activity", "ferment_products", "ferment_energy"]
    pointers = json.loads((REPO / "data/citations/pointers.json").read_text(encoding="utf-8"))["pointers"]
    for cid, page in (("ferment_activity", 125), ("ferment_products", 123), ("ferment_energy", 126)):
        assert pointers[cid]["page"] == page and pointers[cid]["models"] == ["biology.respiration_energy"]
        assert pointers[cid]["topics"] == ["biology_form4_respiration"]


def test_the_planner_schema_describes_the_new_fields() -> None:
    schema = json.loads((REPO / "api/prompts/schemas/plan.schema.json").read_text(encoding="utf-8"))
    assert schema == plan_module.json_schema()
    assert "model" in schema["$defs"]["SceneSpec"]["properties"]
    assert "dial" in json.dumps(schema["$defs"]["ControlSpec"]["properties"]["surface"])
