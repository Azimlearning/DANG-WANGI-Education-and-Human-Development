from __future__ import annotations

import json
from pathlib import Path

import pytest

import api.prompts as prompts
from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline import prompts as pp
from api.pipeline.fill import contract_for
from api.pipeline.plan_checks import PlanIssue

REPO = Path(__file__).resolve().parents[2]
GOLDEN = sorted((REPO / "data" / "plans").glob("*.json"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def test_every_pack_loads_and_validates() -> None:
    names = prompts.all_names()
    assert {
        "core",
        "planner",
        "fill",
        "repair",
        "explainer",
        "verifier_l4",
        "router-fallback",
        "patterns-simulation",
        "patterns-virtual_experiment",
    } <= set(names)
    for name in names:
        p = prompts.load(name)
        assert p.version >= 1 and p.purpose and p.tier in prompts.TIERS and len(p.sha256) == 64


def test_no_pack_uses_a_long_dash() -> None:
    for path in prompts.DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "—" not in text and "–" not in text, path.name


def test_a_pack_over_its_budget_fails_and_so_does_a_placeholder_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompts, "DIR", tmp_path)
    (tmp_path / "big.v1.md").write_text(
        "version: 1\npurpose: x\ntier: any\ninputs:\nbudget: 10\ncache: stable\n---\n" + "word " * 200, encoding="utf-8"
    )
    with pytest.raises(prompts.PromptError, match="budget"):
        prompts.load("big")
    (tmp_path / "bad.v1.md").write_text(
        "version: 1\npurpose: x\ntier: any\ninputs: a\nbudget: 100\ncache: stable\n---\nhello {{b}}", encoding="utf-8"
    )
    with pytest.raises(prompts.PromptError, match="placeholders"):
        prompts.load("bad")
    (tmp_path / "unused.v1.md").write_text(
        "version: 1\npurpose: x\ntier: any\ninputs: a, b\nbudget: 100\ncache: stable\n---\nhello {{a}}",
        encoding="utf-8",
    )
    with pytest.raises(prompts.PromptError, match="placeholders"):
        prompts.load("unused")
    (tmp_path / "tier.v1.md").write_text(
        "version: 1\npurpose: x\ntier: huge\ninputs:\nbudget: 100\ncache: stable\n---\nhi", encoding="utf-8"
    )
    with pytest.raises(prompts.PromptError, match="tier"):
        prompts.load("tier")
    (tmp_path / "nohead.v1.md").write_text("no header here", encoding="utf-8")
    with pytest.raises(prompts.PromptError):
        prompts.load("nohead")
    (tmp_path / "schema.v1.md").write_text(
        "version: 1\npurpose: x\ntier: any\ninputs:\nbudget: 100\ncache: stable\nschema: nope.json\n---\nhi",
        encoding="utf-8",
    )
    with pytest.raises(prompts.PromptError, match="schema"):
        prompts.load("schema")


def test_the_stable_prefix_is_byte_identical_when_only_variables_differ(manifest: kitmanifest.Manifest) -> None:
    a = pp.plan_request("Why does a spring stretch?", "topic=force_and_elasticity", "simulation", manifest)
    b = pp.plan_request(
        "How deep is the pressure in the sea?",
        "topic=forces_and_pressure",
        "simulation",
        manifest,
        issues=[PlanIssue("PLAN-002", "models[0]", "m", "h")],
    )
    assert a.system == b.system and a.system
    assert a.prompt != b.prompt
    assert "spring stretch" not in (a.system or "") and "spring stretch" in a.prompt
    c = pp.plan_request("Why does a spring stretch?", "x", "virtual_experiment", manifest)
    assert c.system != a.system  # a different pattern is a different stable prefix


def test_the_request_embeds_the_schema_and_the_generated_failure_modes(manifest: kitmanifest.Manifest) -> None:
    r = pp.plan_request("q", "r", "simulation", manifest)
    schema = pp.schema_json()
    assert json.dumps(schema, indent=2, sort_keys=True).strip()[:40] in (r.system or "")
    assert "PLAN-002" in (r.system or "") and "{{" not in (r.system or "") + r.prompt


def test_failure_modes_text_comes_from_the_registry_and_is_stable() -> None:
    assert pp.failure_modes_text() == pp.failure_modes_text()
    assert "Use only science models listed in the Kit manifest." in pp.failure_modes_text()


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.stem)
def test_the_kit_pack_for_each_plan_is_exactly_what_it_names_and_at_most_15(
    path: Path, manifest: kitmanifest.Manifest
) -> None:
    plan = plan_module.parse(path.read_text(encoding="utf-8"))
    names = pp.kit_pack_for_plan(plan, manifest)
    assert len(names) <= pp.MAX_KIT_PACK
    assert set(names) >= {"environment", "slider", "readout", "reset", "bridge"} | {
        manifest.models[m.model].export_name for m in plan.models
    }
    assert ("experiment" in names) == (plan.experiment is not None)
    assert ("graph" in names) == bool(plan.graphs)
    assert ("table" in names) == (plan.table is not None)
    assert all(manifest.has(n) for n in names)


@pytest.mark.parametrize(
    ("question", "model"),
    [
        ("Why does a spring stretch when I hang a weight on it?", "hookes"),
        ("How does the pressure change as a diver goes deeper in water?", "pressureDepth"),
        ("What happens to the current if I raise the resistance?", "ohm"),
    ],
)
def test_the_question_kit_pack_finds_the_right_model_and_stays_small(
    question: str, model: str, manifest: kitmanifest.Manifest
) -> None:
    names = pp.kit_pack_for_question(question, "simulation", manifest)
    assert model in names and len(names) <= pp.MAX_KIT_PACK
    topic = next(t for m in manifest.models.values() if m.export_name == model for t in m.topics)
    served = pp.kit_pack_for_question(question, "simulation", manifest, topic=topic)
    base = [n for n in served if n in pp.BASE_COMPONENTS or n in pp.PATTERN_COMPONENTS["simulation"]]
    assert served[len(base)] == model  # with the routed topic, the model that serves it comes first among the models


def test_the_request_builders_stay_inside_the_token_cap(manifest: kitmanifest.Manifest) -> None:
    for request in (
        pp.plan_request("q" * 400, "r", "virtual_experiment", manifest),
        pp.fill_request("extra", "One sentence.", contract_for("extra"), ("env", "c_load")),
        pp.explain_request("Why?", "topic=x"),
    ):
        d = pp.describe(request)
        assert d["system_tokens"] + d["user_tokens"] <= pp.REQUEST_TOKEN_CAP
        assert "q" * 400 not in json.dumps(d)  # the trace record never carries the question


def test_an_oversized_request_is_refused(manifest: kitmanifest.Manifest) -> None:
    with pytest.raises(ValueError, match="cap"):
        pp.plan_request("x" * 40000, "r", "simulation", manifest)
