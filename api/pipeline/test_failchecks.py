"""The registry is tied to the code: every rule string the verifier, post-processor, plan checks and fill checks can emit is registered, and every
registered rule can still be emitted."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from api.pipeline import failchecks as fc

API = Path(__file__).resolve().parents[1]
_ARG_INDEX = {"Problem": 0, "ScanReject": 0, "PostprocessReject": 1, "VerificationFailed": 1}
PIPELINE_LEVEL = {"GAP", "BUDGET", "INTAKE", "WORDING", "FREE_REPLY", "FREE_UNCHECKED"}
"""Rules the orchestrator raises itself (not the verifier or the plan checks). `test_run.py` proves each is actually emitted into the trace."""


def _consts(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _consts(node.body) + _consts(node.orelse)
    return []


def scan_source(src: str, filename: str) -> tuple[set[str], list[str]]:
    """The rule strings one source file can emit, and the call sites whose rule is NOT a string constant (they would evade this test)."""
    consts: set[str] = set()
    dynamic: list[str] = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call):
            name = getattr(n.func, "id", getattr(n.func, "attr", None))
            idx = _ARG_INDEX.get(name or "")
            if idx is not None and len(n.args) > idx:
                found = _consts(n.args[idx])
                if found:
                    consts |= set(found)
                else:
                    dynamic.append(f"{filename}:{n.lineno} {name}({ast.unparse(n.args[idx])})")
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple) and n.value.elts and filename == "render.py":
            consts |= set(_consts(n.value.elts[0]))
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "rule" for t in n.targets):
            consts |= set(_consts(n.value))
    return consts, dynamic


def _verifier_files() -> list[Path]:
    return [
        f
        for f in [*(API / "verify").glob("*.py"), API / "postprocess.py"]
        if not f.name.startswith(("test_", "conftest"))
    ]


def emitted_by_verifier() -> set[str]:
    out: set[str] = set()
    for f in _verifier_files():
        out |= scan_source(f.read_text(encoding="utf-8"), f.name)[0]
    return out


def dynamic_sites() -> list[str]:
    out: list[str] = []
    for f in _verifier_files():
        out += scan_source(f.read_text(encoding="utf-8"), f.name)[1]
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


def test_the_scanner_is_not_vacuous_and_finds_a_rule_added_without_a_registry_entry() -> None:
    found = emitted_by_verifier()
    assert len(found) >= 40, f"the scan found only {len(found)} rules; it has probably stopped seeing the code"
    rule = "a_brand_new_rule_nobody_registered"
    synthetic = f'raise VerificationFailed("render", "{rule}", "reason")\nraise ScanReject("{rule}2", "x")\n'
    consts, dynamic = scan_source(synthetic, "synthetic.py")
    assert consts == {rule, rule + "2"} and dynamic == []
    assert (found | consts) - set(fc.REGISTRY) == {
        rule,
        rule + "2",
    }  # this is exactly what the coverage test would report


# Each of these re-wraps a rule that another, scanned call site already produced as a string constant (the L0 scan's ScanReject, chain_problem and
# input_unit_problems in provenance.py, the gate re-raising guard_label's failure). They are pinned by file and expression, so a NEW dynamic site
# fails here until someone checks where its rule comes from.
REVIEWED_DYNAMIC = {
    "provenance.py Problem(found.rule)",
    "provenance.py Problem(p.rule)",
    "postprocess.py PostprocessReject(hit.rule)",
    "gate.py VerificationFailed(failure.rule)",
    "gate.py VerificationFailed(hit.rule)",
    "mint.py VerificationFailed(processed.rule)",
    "mint.py VerificationFailed(refusal[0])",
}


def test_a_rule_passed_as_a_variable_is_seen_as_dynamic_and_new_ones_must_be_reviewed() -> None:
    consts, dynamic = scan_source('raise VerificationFailed("gate", some_variable, "x")', "synthetic.py")
    assert consts == set() and len(dynamic) == 1
    seen = {site.split(":", 1)[0] + " " + site.split(" ", 1)[1] for site in dynamic_sites()}
    assert seen <= REVIEWED_DYNAMIC, f"new dynamic rule sites need review: {sorted(seen - REVIEWED_DYNAMIC)}"


def test_every_rule_the_orchestrator_raises_itself_is_registered_and_each_registered_pipeline_rule_is_raised_there() -> None:
    """`PIPELINE_LEVEL` rules are not emitted by the verifier or the checks, so they were exempt from the coverage test. This closes that: they are read out
    of `run.py` (`failchecks.get("X")`, `degrade("X")`), so a rule that stops being raised, or one raised but never registered, fails here."""
    source = (API / "pipeline" / "run.py").read_text(encoding="utf-8")
    raised = set(re.findall(r'(?:failchecks\.get|degrade)\(\s*"([A-Z_]+)"', source))
    assert raised, "the scan found nothing in run.py; it has probably stopped seeing the code"
    assert raised <= set(fc.REGISTRY), f"raised but not registered: {sorted(raised - set(fc.REGISTRY))}"
    # `GAP` is the registry's entry for an assembly gap, which the orchestrator handles by branch (and logs by part), not by naming the rule.
    named = PIPELINE_LEVEL - {"GAP"}
    assert named <= raised, f"registered as raised by the orchestrator but never raised there: {sorted(named - raised)}"
