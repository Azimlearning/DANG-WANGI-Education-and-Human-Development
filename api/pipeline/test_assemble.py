from __future__ import annotations

import json
from pathlib import Path

import pytest

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import AssemblyGap, assemble, js
from api.pipeline.plan import Plan
from api.schema.generated import Citation
from api.verify.mint import verify_environment

REPO = Path(__file__).resolve().parents[2]
GOLDEN = sorted((REPO / "data" / "plans").glob("*.json"))
ORIGIN = "http://localhost:3000"


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def load(path: Path) -> Plan:
    return plan_module.parse(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.stem)
def test_each_golden_plan_is_assembled_with_no_model_and_minted_by_the_real_verifier(
    path: Path, manifest: kitmanifest.Manifest, kit_dist: Path
) -> None:
    plan = load(path)
    page = assemble(plan, manifest)
    assert page.html.startswith("<!doctype html>") and f"/vendor/kit/{manifest.version}/core.js" in page.html
    env = verify_environment(
        slug=plan.id,
        title=plan.title,
        raw_html=page.html,
        lane="instantiate",
        label="model-checked",
        kit_version=manifest.version,
        citations=[Citation(source="UNVERIFIED (corpus not loaded until P2)", page=None, quote=None, verified=False)],
        plan_summary=plan.goal,
        public_origin=ORIGIN,
        kit_dist=kit_dist,
        interaction_seconds=1.0,
        plan_models=plan.model_summaries(),
    )
    assert env.checked.reference_cases > 0
    assert set(env.checked.layers) >= {"postprocess", "scan", "render", "provenance", "grid", "reference"}
    assert env.checked.models and {m[0] for m in env.checked.models} == {m.model for m in plan.models}


def test_the_assembled_page_is_a_pure_function_of_the_plan(manifest: kitmanifest.Manifest) -> None:
    plan = load(GOLDEN[0])
    assert assemble(plan, manifest).html == assemble(plan, manifest).html


def test_every_plan_word_appears_in_the_page_and_no_other_script_is_written(manifest: kitmanifest.Manifest) -> None:
    plan = load(next(p for p in GOLDEN if "hookes" in p.name))
    page = assemble(plan, manifest).html
    for text in (plan.title, plan.note, *plan.sentences, *plan.steps):
        assert js(text)[1:-1] in page
    assert page.count("<script") == 2  # the Kit, then the one inline script


def test_plan_text_cannot_break_out_of_the_script(manifest: kitmanifest.Manifest) -> None:
    d = json.loads(GOLDEN[0].read_text())
    d["sentences"] = ['Close </script><script>alert("x")</script> here.']
    page = assemble(Plan.model_validate(d), manifest).html
    assert page.count("</script>") == 2 and "<\\/script>" in page


def test_a_pattern_without_a_skeleton_or_a_part_the_skeleton_cannot_take_is_a_gap(
    manifest: kitmanifest.Manifest,
) -> None:
    d = json.loads(next(p for p in GOLDEN if "ohm" in p.name).read_text())
    d["experiment"] = json.loads(next(p for p in GOLDEN if "hookes" in p.name).read_text())["experiment"]
    with pytest.raises(AssemblyGap) as err:
        assemble(Plan.model_validate(d), manifest)  # a simulation has no experiment card slot
    assert err.value.part == "experiment"


def test_a_custom_slot_without_a_fill_is_a_gap_and_with_a_fill_is_placed(manifest: kitmanifest.Manifest) -> None:
    d = json.loads(next(p for p in GOLDEN if "ohm" in p.name).read_text())
    d["custom"] = [{"name": "extra", "purpose": "One more sentence for the stage."}]
    plan = Plan.model_validate(d)
    with pytest.raises(AssemblyGap):
        assemble(plan, manifest)
    page = assemble(plan, manifest, {"extra": 'Synapse.text(env, "Try it.");'})
    assert "/* custom: extra */" in page.html and 'Synapse.text(env, "Try it.");' in page.html
    assert "env" in page.scope and "c_voltage" in page.scope and "m_conductor" in page.scope


def test_plan_text_that_looks_like_a_slot_or_variable_is_never_substituted(manifest: kitmanifest.Manifest) -> None:
    d = json.loads(GOLDEN[0].read_text())
    d["note"] = "See {{title}} and {{nope}} and /*SLOT:custom*/ here."
    d["title"] = "A /*SLOT:steps*/ title {{kit_version}}"
    page = assemble(plan_module.parse(json.dumps(d)), manifest).html
    assert "{{nope}}" in page and "{{title}}" in page and "{{kit_version}}" in page
    assert page.count("/*SLOT:") == 3  # the plan wrote one in the note and the title (head and script); all inert text


def test_regression_a_control_range_whose_step_is_a_repeating_decimal_still_verifies(
    manifest: kitmanifest.Manifest, kit_dist: Path
) -> None:
    """Found by eval/plans/fuzz.py: min 6, max 14, grid 3 gives a step of 2.666..., which the browser's range input could not reach max with."""
    d = json.loads((next(p for p in GOLDEN if "osmosis" in p.name)).read_text())
    d["controls"][0].update({"min": 6, "max": 14, "value": 12, "grid": 3})
    plan = plan_module.parse(json.dumps(d))
    env = verify_environment(
        slug=plan.id,
        title=plan.title,
        raw_html=assemble(plan, manifest).html,
        lane="compose",
        label="model-checked",
        kit_version=manifest.version,
        citations=[Citation(source="UNVERIFIED (corpus not loaded until P2)", page=None, quote=None, verified=False)],
        plan_summary=plan.goal,
        public_origin=ORIGIN,
        kit_dist=kit_dist,
        interaction_seconds=1.0,
        plan_models=plan.model_summaries(),
    )
    assert env.checked.grid_points >= 4
