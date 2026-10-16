"""The registry is tied to the code: every rule string the verifier, post-processor, plan checks and fill checks can emit is registered, and every
registered rule can still be emitted."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from api.pipeline import failchecks as fc

API = Path(__file__).resolve().parents[1]
_ARG_INDEX = {"Problem": 0, "ScanReject": 0, "PostprocessReject": 1, "VerificationFailed": 1}
PIPELINE_LEVEL = {"GAP", "BUDGET", "INTAKE"}


def _consts(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _consts(node.body) + _consts(node.orelse)
    return []


def emitted_by_verifier() -> set[str]:
    files = [
        f
        for f in [*(API / "verify").glob("*.py"), API / "postprocess.py"]
        if not f.name.startswith(("test_", "conftest"))
    ]
    out: set[str] = set()
    for f in files:
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call):
                name = getattr(n.func, "id", getattr(n.func, "attr", None))
                idx = _ARG_INDEX.get(name or "")
                if idx is not None and len(n.args) > idx:
                    out |= set(_consts(n.args[idx]))
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple) and n.value.elts and f.name == "render.py":
                out |= set(_consts(n.value.elts[0]))
            if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "rule" for t in n.targets):
                out |= set(_consts(n.value))
    return out


def emitted_codes(path: Path, prefix: str) -> set[str]:
    return set(re.findall(rf'"({prefix}-\d+)"', path.read_text(encoding="utf-8")))


def test_every_rule_the_verifier_can_emit_is_registered() -> None:
    missing = emitted_by_verifier() - set(fc.REGISTRY)
    assert not missing, f"unregistered rules: {sorted(missing)}; add them to api/pipeline/failchecks.py"


def test_every_plan_and_fill_code_is_registered() -> None:
    plan = emitted_codes(API / "pipeline" / "plan_checks.py", "PLAN")
    fill = emitted_codes(API / "pipeline" / "fill.py", "FILL")
    assert plan and fill
    assert not (plan | fill) - set(fc.REGISTRY), sorted((plan | fill) - set(fc.REGISTRY))


def test_every_registered_rule_can_still_be_emitted() -> None:
    reachable = (
        emitted_by_verifier()
        | emitted_codes(API / "pipeline" / "plan_checks.py", "PLAN")
        | emitted_codes(API / "pipeline" / "fill.py", "FILL")
        | PIPELINE_LEVEL
    )
    stale = set(fc.REGISTRY) - reachable
    assert not stale, f"registered but never emitted: {sorted(stale)}"


def test_codes_are_unique_and_every_entry_is_complete() -> None:
    codes = [f.code for f in fc.REGISTRY.values()]
    assert len(codes) == len(set(codes))
    for f in fc.REGISTRY.values():
        assert f.model_hint and f.student_message and f.layer
        assert "—" not in f.student_message and "–" not in f.student_message and "—" not in f.model_hint


def test_an_unknown_rule_reads_as_a_pipeline_bug_not_an_invented_entry() -> None:
    got = fc.get("made_up_rule")
    assert got.code == "PIPE-999" and got.repair == "none"


def test_the_coverage_test_bites(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """If the registry lost an entry the first test would fail: prove the mechanism by removing one."""
    smaller = {k: v for k, v in fc.REGISTRY.items() if k != "dead_control"}
    monkeypatch.setattr(fc, "REGISTRY", smaller)
    assert "dead_control" in emitted_by_verifier() - set(fc.REGISTRY)
