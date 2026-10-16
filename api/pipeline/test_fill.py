from __future__ import annotations

from pathlib import Path

import pytest

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.pipeline.fill import check_fill, contract_for
from api.schema.generated import Citation
from api.verify.mint import VerificationFailed, verify_environment

REPO = Path(__file__).resolve().parents[2]
SCOPE = ("env", "c_voltage", "c_resistance", "m_conductor")
C = contract_for("extra")


def codes(code: str) -> list[str]:
    return [i.code for i in check_fill(code, C, SCOPE)]


def test_a_plain_kit_call_passes_the_contract() -> None:
    assert codes('Synapse.text(env, "Try a resistance of 4 ohm.");') == []
    assert codes("var half = c_voltage;\n  Synapse.text(env, 'Half way.');") == []


def test_a_forbidden_function_is_fill_002() -> None:
    assert "FILL-002" in codes('fetch("https://example.com");')
    assert "FILL-002" in codes("document.cookie")


def test_a_kit_call_the_slot_does_not_allow_is_fill_003() -> None:
    assert "FILL-003" in codes("Synapse.slider(env, {});")
    assert "FILL-003" in codes("Synapse.audit();")


def test_an_undeclared_identifier_is_fill_004() -> None:
    assert "FILL-004" in codes("Synapse.text(env, secret);")
    assert "FILL-004" in codes("ghost.set(3);")
    assert codes("var f = function (a) { return a; };") == []


def test_empty_unbalanced_and_markup_fills_are_fill_005_and_006() -> None:
    assert codes("   ") == ["FILL-005"]
    assert "FILL-005" in codes("Synapse.text(env, 'x';")
    assert "FILL-006" in codes("</script><script>1</script>")


def test_a_too_long_fill_is_fill_001() -> None:
    assert "FILL-001" in codes("\n".join(["var a = 1;"] * 20))
    assert "FILL-001" in codes("var a = '" + "x" * 900 + "';")


def test_strings_and_comments_do_not_count_as_code() -> None:
    assert codes('Synapse.text(env, "ghost and fetch are only words here"); // eval') == []


def test_a_valid_fill_is_inserted_and_the_page_is_minted_and_a_bad_one_never_reaches_assembly(kit_dist: Path) -> None:
    import json

    manifest = kitmanifest.load(kit_dist, latest_version(kit_dist))
    d = json.loads((REPO / "data/plans/physics-f5-ohm_explorer.json").read_text())
    d["custom"] = [{"name": "extra", "purpose": "One more sentence."}]
    plan = plan_module.Plan.model_validate(d)
    fill = 'Synapse.text(env, "Try a voltage of 12 V.");'
    assert check_fill(fill, C, assemble(plan, manifest, {"extra": fill}).scope) == []
    page = assemble(plan, manifest, {"extra": fill})
    env = verify_environment(
        slug=plan.id,
        title=plan.title,
        raw_html=page.html,
        lane="instantiate",
        label="model-checked",
        kit_version=manifest.version,
        citations=[Citation(source="UNVERIFIED", page=None, quote=None, verified=False)],
        plan_summary=plan.goal,
        public_origin="http://localhost:3000",
        kit_dist=kit_dist,
        interaction_seconds=1.0,
        plan_models=plan.model_summaries(),
    )
    assert env.env_id
    # A fill that passes the contract but states an unbacked number is still refused by the page verifier.
    bad = assemble(plan, manifest, {"extra": 'Synapse.text(env, "The current is 7.3 A.");'})
    assert check_fill('Synapse.text(env, "The current is 7.3 A.");', C, bad.scope) == []
    with pytest.raises(VerificationFailed) as err:
        verify_environment(
            slug=plan.id,
            title=plan.title,
            raw_html=bad.html,
            lane="instantiate",
            label="model-checked",
            kit_version=manifest.version,
            citations=[Citation(source="UNVERIFIED", page=None, quote=None, verified=False)],
            plan_summary=plan.goal,
            public_origin="http://localhost:3000",
            kit_dist=kit_dist,
            interaction_seconds=1.0,
            plan_models=plan.model_summaries(),
        )
    assert err.value.rule == "unbacked_copy_number"


# ── bypass probes (S-notes): every one of these must be refused AT THE CONTRACT, so the model gets early, named feedback ──────────────────
PROBES = {
    "alias Synapse": "const s = Synapse; s.lockdown();",
    "pass Synapse to Object.assign": "Object.assign(Synapse, {x: 1});",
    "constructor chain": 'this.constructor.constructor("return 1")();',
    "__proto__": "({}).__proto__.polluted = 1;",
    "prototype": "Array.prototype.map = null;",
    "defineProperty": 'Object.defineProperty(Synapse, "text", {value: 1});',
    "getPrototypeOf": "Object.getPrototypeOf(Math).x = 1;",
    "template substitution": "Synapse.text(`${globalThis.top}`);",
    "string hides code after //": 'var a = "x//"; Function("return 1")();',
    "unicode escape in a name": "Synapse.\\u0074ext(1);",
    "string-keyed access": 'Math["con"+"structor"]["constructor"]("1")();',
    "string key on a variable": 'var o = Object; o["keys"](Synapse);',
    "unterminated string": 'var a = "x; Function("1")();',
    "regex literal with a quote": 'var r = /"/; Function("1")();',
    "with statement": "with (Math) { PI; }",
    "indirect eval": '(0, eval)("1");',
    "setTimeout with a string": 'setTimeout("1", 0);',
    "dynamic import": 'import("/x.js");',
    "new Function": 'new Function("return 1")();',
    "Reflect": "Reflect.ownKeys(Math);",
    "Proxy": "new Proxy({}, {});",
}


@pytest.mark.parametrize("name", sorted(PROBES))
def test_each_bypass_probe_is_refused_by_the_contract(name: str) -> None:
    issues = check_fill(PROBES[name], contract_for("x"), ("load", "k", "env"))
    assert issues, f"{name} passed the contract"


def test_ordinary_fills_still_pass_and_a_string_with_slashes_is_not_a_comment() -> None:
    scope = ("load", "k", "env")
    ok = [
        'Synapse.text(env, { text: "Hello " + load.get() });',
        "var d = Math.round(load.get() * 2);\nSynapse.text(env, { text: d + 1 });",
        'Synapse.text(env, { text: "a//b is not a comment" }); // a real comment',
        'var a = [1, 2, 3]; var b = a[1] + a[0]; Synapse.text(env, { text: "x" + b });',
    ]
    for code in ok:
        assert check_fill(code, contract_for("x"), scope) == [], code
