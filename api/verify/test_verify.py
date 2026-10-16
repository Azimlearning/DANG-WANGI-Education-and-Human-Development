"""The trust path end to end: the good fixture is minted, stored and delivered; each planted defect is refused at its named
layer; a stored Environment changed by one byte is refused; the mint cannot be used outside the verifier."""

from __future__ import annotations

import ast
import copy
import hashlib
import pickle
import shutil
import sqlite3
from pathlib import Path

import pytest

from api import postprocess
from api.kit import latest_version
from api.schema.generated import Citation, EnvironmentBlock
from api.verify.conftest import ORIGIN, mint
from api.verify.gate import deliver
from api.verify.mint import MintRefused, VerificationFailed, VerifiedEnvironment, html_sha256
from api.verify.store import SqliteEnvironmentStore

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def minted(kit_dist: Path) -> VerifiedEnvironment:
    # The default 10 s scripted interaction, once, to prove the full time box runs.
    from api.verify.conftest import fixture_html
    from api.verify.mint import verify_environment

    return verify_environment(
        slug="reference-spring",
        title="Why does a spring stretch?",
        raw_html=fixture_html("reference-spring.html"),
        lane="instantiate",
        label="model-checked",
        kit_version=latest_version(kit_dist),
        plan_models=[{"id": "mechanics.hookes", "params": {"k": 50}}],
        citations=[Citation(source="UNVERIFIED (corpus not loaded until P2)", page=None, quote=None, verified=False)],
        plan_summary="A hand-written fixture.",
        public_origin=ORIGIN,
        kit_dist=kit_dist,
    )


def test_good_fixture_is_minted_with_what_was_checked(minted: VerifiedEnvironment) -> None:
    assert minted.label == "model-checked"
    assert minted.checked.layers == ("postprocess", "scan", "render", "provenance", "grid", "reference")
    assert minted.checked.grid_points >= 11  # the load slider's whole grid plus the extremes
    assert minted.checked.reference_cases == minted.checked.grid_points  # one readout, compared at every position
    assert minted.checked.models == (("mechanics.hookes", (("k", 50.0),)),)
    assert minted.checked.controls_exercised == 1
    assert minted.checked.readouts == 1
    assert minted.checked.interaction_seconds >= 10.0
    assert html_sha256(minted.html) == minted.html_sha256


def test_good_fixture_is_stored_and_the_gate_returns_a_block_with_the_stored_hash(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    stored = store.put_verified(minted)
    block = deliver(store, minted.env_id, public_origin=ORIGIN, kit_dist=kit_dist)
    assert isinstance(block, EnvironmentBlock)
    assert block.htmlSha256 == stored.html_sha256 == minted.html_sha256
    assert html_sha256(block.html) == block.htmlSha256
    assert block.label == "model-checked"
    assert block.lane == "instantiate"
    assert block.citations[0].verified is False


def test_stored_environment_is_never_replaced(minted: VerifiedEnvironment, tmp_path: Path) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_verified(minted)
    store.put_verified(minted)
    assert store.counts() == {"verified": 1}


def test_bad_fetch_is_refused_at_scan_naming_the_api(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-fetch.html")
    assert err.value.stage == "scan"
    assert "fetch" in err.value.reason


def test_bad_dead_control_is_refused_at_render_naming_the_control(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-dead-control.html")
    assert err.value.stage == "render"
    assert err.value.rule == "dead_control"
    assert "'load'" in err.value.reason


def test_bad_bypass_is_now_refused_by_l1_as_a_readout_mismatch(kit_dist: Path) -> None:
    """P0 could only document this gap: a hand-typed wrong number in a readout moves with the slider, so the render layer saw nothing
    wrong. L1 compares the text with the value the Kit formats from the observable, so it is refused (flipped from the P0 test)."""
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-bypass.html")
    assert (err.value.stage, err.value.rule) == ("render", "readout_mismatch")
    assert "0.400 m" in err.value.reason and "0.200 m" in err.value.reason


def test_one_byte_tamper_of_the_stored_html_is_refused_by_the_gate(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    db = tmp_path / "envs.db"
    store = SqliteEnvironmentStore(db)
    store.put_verified(minted)
    assert "Extension" in minted.html
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE environments SET html = replace(html, 'Extension', 'Extensioz')")
    assert store.get(minted.env_id) is None  # the store's own check
    with pytest.raises(VerificationFailed) as err:
        deliver(store, minted.env_id, public_origin=ORIGIN, kit_dist=kit_dist)
    assert err.value.stage == "gate"
    assert err.value.rule == "hash_mismatch"


def test_gate_rescans_a_row_whose_hash_and_id_were_rewritten_to_match(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    """An attacker who edits the row consistently (new HTML, new hash, new id) still meets the L0 scan on delivery."""
    db = tmp_path / "envs.db"
    store = SqliteEnvironmentStore(db)
    store.put_verified(minted)
    evil = minted.html.replace("Synapse.bridge.ready();", "fetch('/x'); Synapse.bridge.ready();")
    sha = html_sha256(evil)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE environments SET html = ?, html_sha256 = ?, env_id = ?",
            (evil, sha, f"reference-spring-{sha[:12]}"),
        )
    with pytest.raises(VerificationFailed) as err:
        deliver(store, f"reference-spring-{sha[:12]}", public_origin=ORIGIN, kit_dist=kit_dist)
    assert err.value.stage == "gate"
    assert "fetch" in err.value.reason


def test_gate_refuses_a_forged_label_in_the_row(minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path) -> None:
    db = tmp_path / "envs.db"
    store = SqliteEnvironmentStore(db)
    store.put_verified(minted)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE environments SET label = 'canonical'")
    with pytest.raises(VerificationFailed) as err:
        deliver(store, minted.env_id, public_origin=ORIGIN, kit_dist=kit_dist)
    assert err.value.rule == "needs_human"


def test_gate_refuses_when_the_public_origin_changed(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_verified(minted)
    with pytest.raises(VerificationFailed) as err:
        deliver(store, minted.env_id, public_origin="https://other.example", kit_dist=kit_dist)
    assert err.value.rule == "csp_mismatch"


def test_gate_refuses_an_unbuilt_kit_version(minted: VerifiedEnvironment, tmp_path: Path) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_verified(minted)
    empty = tmp_path / "no-kit"
    empty.mkdir()
    with pytest.raises(VerificationFailed) as err:
        deliver(store, minted.env_id, public_origin=ORIGIN, kit_dist=empty)
    assert err.value.rule == "stale_kit"


def test_gate_refuses_an_unknown_id(tmp_path: Path, kit_dist: Path) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    with pytest.raises(VerificationFailed) as err:
        deliver(store, "nope", public_origin=ORIGIN, kit_dist=kit_dist)
    assert err.value.rule == "not_found"


def test_rejected_html_is_kept_for_audit_and_never_served(tmp_path: Path, kit_dist: Path) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_rejected("reference-spring", "<html>bad</html>", "scan", "forbidden_api", "forbidden API(s): fetch")
    assert store.counts() == {"rejected": 1}
    assert store.rejected()[0]["reason"].startswith("scan/forbidden_api")
    assert store.get_record(f"rejected-reference-spring-{html_sha256('<html>bad</html>')[:12]}") is None


# ── the mint ────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_a_verified_environment_cannot_be_constructed_outside_the_verifier() -> None:
    with pytest.raises(MintRefused):
        VerifiedEnvironment()
    with pytest.raises(MintRefused):
        VerifiedEnvironment(_mint=object(), env_id="x")  # type: ignore[call-arg]


def test_a_verified_environment_resists_subclassing_assignment_copying_and_pickling(
    minted: VerifiedEnvironment,
) -> None:
    with pytest.raises(TypeError):

        class Sub(VerifiedEnvironment):  # type: ignore[misc, valid-type]
            pass

    with pytest.raises(AttributeError):
        minted.html = "<html></html>"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del minted.html  # type: ignore[misc]
    with pytest.raises(TypeError):
        copy.copy(minted)
    with pytest.raises(TypeError):
        copy.deepcopy(minted)
    with pytest.raises(TypeError):
        pickle.dumps(minted)
    # Hardening, not a guarantee: `object.__setattr__` and the closure cell bypass it from inside the process. The mint docstring
    # says so; the delivery gate, not this class, is what protects the client.


def test_the_store_refuses_anything_that_is_not_a_verified_environment(tmp_path: Path) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    with pytest.raises(TypeError):
        store.put_verified({"env_id": "x"})  # type: ignore[arg-type]


def _is_name(node: ast.AST, name: str) -> bool:
    return (isinstance(node, ast.Name) and node.id == name) or (isinstance(node, ast.Attribute) and node.attr == name)


def test_the_mint_issuer_and_constructor_appear_only_in_the_verifier_source() -> None:
    """AST scan of api/ and eval/: `_issue` is never referenced outside api/verify/mint.py (by name, attribute, import or string),
    nobody introspects `__closure__`, and outside tests `VerifiedEnvironment` is never called or aliased. Test files may CALL it to
    prove it refuses. This file is excluded because it names what it looks for."""
    offenders: list[str] = []
    skip = {Path(__file__).resolve(), (REPO / "api" / "verify" / "mint.py").resolve()}
    for root in ("api", "eval"):
        for path in sorted((REPO / root).rglob("*.py")):
            if path.resolve() in skip:
                continue
            is_test = path.name.startswith("test_") or path.name == "conftest.py"
            rel = str(path.relative_to(REPO))
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                line = getattr(node, "lineno", 0)
                if _is_name(node, "_issue") or (isinstance(node, ast.Constant) and node.value == "_issue"):
                    offenders.append(f"{rel}:{line}: _issue")
                if isinstance(node, (ast.ImportFrom, ast.Import)) and any(a.name == "_issue" for a in node.names):
                    offenders.append(f"{rel}:{line}: imports _issue")
                if isinstance(node, ast.Attribute) and node.attr in ("__closure__", "cell_contents"):
                    offenders.append(f"{rel}:{line}: closure introspection")
                if not is_test:
                    if isinstance(node, ast.Call) and _is_name(node.func, "VerifiedEnvironment"):
                        offenders.append(f"{rel}:{line}: VerifiedEnvironment(")
                    if (
                        isinstance(node, (ast.Assign, ast.AnnAssign))
                        and node.value is not None
                        and _is_name(node.value, "VerifiedEnvironment")
                    ):
                        offenders.append(f"{rel}:{line}: alias of VerifiedEnvironment")
    assert offenders == []


def test_the_scan_would_catch_an_alias_and_a_closure_peek(tmp_path: Path) -> None:
    """The scanner itself is checked against the evasions kit-guardian found (`cls = VerifiedEnvironment; cls(...)`)."""
    tree = ast.parse("cls = VerifiedEnvironment\ncls()\nx = VerifiedEnvironment.__init__.__closure__[0].cell_contents")
    found = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and _is_name(n.value, "VerifiedEnvironment")]
    peeks = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in ("__closure__", "cell_contents")]
    assert found and len(peeks) == 2


# ── labels and grounding (hard constraints 3 and 4) ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("label", "rule"),
    [
        ("canonical", "needs_human"),
        ("reviewed", "needs_human"),
        ("kit-verified", "ungrounded"),
        ("dev-fixture", "unreachable"),
    ],
)
def test_only_dev_fixture_is_reachable_in_p0(kit_dist: Path, label: str, rule: str) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, label=label)
    assert err.value.stage == "label"
    assert err.value.rule == rule


def test_free_lane_can_never_be_kit_verified(kit_dist: Path) -> None:
    cited = [Citation(source="Physics F4", page=12, quote="x", verified=True)]
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, lane="free", label="kit-verified", citations=cited)
    assert err.value.rule == "free_lane"


def test_kit_version_must_be_built_and_match_the_html(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, kit_version="9.9.9")
    assert err.value.stage == "kit"
    assert err.value.rule == "unknown_version"


# ── the injected CSP ────────────────────────────────────────────────────────────────────────────────────────────────


def test_the_injected_csp_equals_the_expected_string_and_names_public_origin() -> None:
    expected = (
        "default-src 'none'; "
        "script-src 'unsafe-inline' http://localhost:3000/vendor/; "
        "style-src 'unsafe-inline'; "
        "img-src data:; "
        "font-src http://localhost:3000/vendor/ data:; "
        "connect-src 'none'; frame-src 'none'; object-src 'none'; "
        "base-uri 'none'; form-action 'none';"
    )
    assert postprocess.build_csp("http://localhost:3000") == expected
    assert postprocess.build_csp("http://localhost:3000/") == expected  # a trailing slash is normalised
    assert "https://example.org/vendor/" in postprocess.build_csp("https://example.org")


@pytest.mark.parametrize("bad", ["localhost:3000", "http://localhost:3000/app", "ftp://x", "", "http://"])
def test_public_origin_must_be_a_bare_origin(bad: str) -> None:
    with pytest.raises(ValueError):
        postprocess.normalise_origin(bad)


def test_a_model_written_csp_is_replaced_by_ours(kit_dist: Path) -> None:
    from api.verify.conftest import fixture_html

    sneaky = fixture_html("reference-spring.html").replace(
        "<head>", '<head><meta http-equiv="Content-Security-Policy" content="default-src *">'
    )
    env = mint(kit_dist, raw_html=sneaky)
    assert env.html.count("Content-Security-Policy") == 1
    assert "default-src *" not in env.html
    assert postprocess.csp_tag(ORIGIN) in env.html


def test_postprocess_adds_viewport_and_charset_and_one_doctype() -> None:
    out = postprocess.run(
        '<html><head></head><body><script src="/vendor/kit/0.0.1/core.js"></script></body></html>', public_origin=ORIGIN
    )
    assert not isinstance(out, postprocess.PostprocessReject)
    assert out.startswith("<!doctype html>")
    assert 'name="viewport"' in out
    assert 'charset="utf-8"' in out


def test_two_html_documents_are_refused() -> None:
    out = postprocess.run("<html></html><html></html>", public_origin=ORIGIN)
    assert isinstance(out, postprocess.PostprocessReject)
    assert out.rule == "single_document"


def test_an_oversized_environment_is_refused() -> None:
    out = postprocess.run("<html><head></head><body>" + "x" * 300_000 + "</body></html>", public_origin=ORIGIN)
    assert isinstance(out, postprocess.PostprocessReject)
    assert out.rule == "size_cap"


# ── kit-guardian findings (review of 0695052) ───────────────────────────────────────────────────────────────────────


def test_B1_a_head_inside_a_comment_cannot_switch_the_csp_off(kit_dist: Path) -> None:
    """The comment is stripped, the CSP lands after the REAL <head>, and the hidden eval is blocked, so the document is refused."""
    from api.verify.conftest import fixture_html

    raw = fixture_html("reference-spring.bad-csp-comment.html")
    processed = postprocess.run(raw, public_origin=ORIGIN)
    assert isinstance(processed, str)
    assert "<!--" not in processed
    assert postprocess.csp_is_first(processed, ORIGIN)
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-csp-comment.html")
    assert err.value.stage == "render"  # the eval threw because the CSP is in force; without a CSP this was minted


@pytest.mark.parametrize(
    ("doc", "rule"),
    [
        ("<!doctype html><title><head></title><html><body></body></html>", "csp_position"),
        ("<![CDATA[ x ]]><html></html>", "markup_declaration"),
        ("<html><!-- never closed", "comment"),
        ("<?xml version='1.0'?><html></html>", "markup_declaration"),
    ],
)
def test_B1_ambiguous_markup_is_refused_not_guessed_at(doc: str, rule: str) -> None:
    out = postprocess.run(doc, public_origin=ORIGIN)
    assert isinstance(out, postprocess.PostprocessReject)
    assert out.rule == rule


def test_B1_csp_is_first_rejects_a_csp_placed_after_a_script() -> None:
    tag = postprocess.csp_tag(ORIGIN)
    assert postprocess.csp_is_first(f"<!doctype html><html><head>{tag}</head><body></body></html>", ORIGIN)
    assert not postprocess.csp_is_first(f"<!doctype html><html><head><script>1</script>{tag}</head></html>", ORIGIN)
    assert not postprocess.csp_is_first(f"<!doctype html><html><head>{tag}{tag}</head></html>", ORIGIN)
    assert not postprocess.csp_is_first("<!doctype html><html><head></head></html>", ORIGIN)


def test_B2_literal_navigation_is_refused_at_scan(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-navigate-literal.html")
    assert err.value.stage == "scan"
    assert "location assignment" in err.value.reason


def test_B2_obfuscated_navigation_is_caught_by_a_real_click_in_the_harness(kit_dist: Path) -> None:
    """`window['loc'+'ation'] = ...` passes the text scan. The harness now presses real input, so the handler runs and the frame
    leaving its document is a refusal. Residual risk (stated in STATUS): a handler that fires only on a condition the harness
    never reaches still passes; closing that needs isolation (A-10), not more patterns."""
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-navigate-obfuscated.html")
    assert err.value.stage == "render"
    assert err.value.rule in ("navigation", "blocked_request")


@pytest.mark.parametrize(
    ("snippet", "label"),
    [
        ("location = 'x'", "location assignment"),
        ("document.location.href", "window.location"),
        ("self.location", "window.location"),
        ("Function('x')", "Function constructor"),
        ("parent.postMessage(1, '*')", "postMessage"),
        ("document.write('x')", "document.write"),
        ("setTimeout('x', 1)", "string timer (eval)"),
    ],
)
def test_new_l0_patterns_name_what_they_catch(snippet: str, label: str) -> None:
    from api.verify import scan

    hit = scan.scan(f"<script>{snippet}</script>")
    assert hit is not None
    assert label in hit.reason


def test_N1_what_is_scanned_is_what_is_minted() -> None:
    """A CSP-shaped fragment inside `new Function(` used to hide the word from the mint-time scan but not from the gate's."""
    doc = '<html><head></head><body><script>new<meta http-equiv="Content-Security-Policy" content="x">\nFunction(1)</script></body></html>'
    out = postprocess.run(doc, public_origin=ORIGIN)
    assert isinstance(out, postprocess.PostprocessReject)
    assert out.stage == "scan"


def test_S1_an_undeclared_control_is_refused(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-undeclared-control.html")
    assert (err.value.stage, err.value.rule) == ("render", "undeclared_control")


def test_S1_a_readout_that_changes_by_itself_does_not_make_a_dead_control_look_wired(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-selfmutating-readout.html")
    assert (err.value.stage, err.value.rule) == ("render", "unstable_readout")


def test_S6_unnamed_controls_and_readouts_are_refused(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, "reference-spring.bad-a11y.html")
    assert (err.value.stage, err.value.rule) == ("render", "a11y")
    assert "accessible name" in err.value.reason


def test_S2_a_kit_whose_bytes_changed_under_the_same_semver_makes_stored_environments_stale(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path, kit_version: str
) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_verified(minted)
    altered = tmp_path / "kit"
    shutil.copytree(kit_dist, altered)
    core = altered / kit_version / "core.js"
    core.write_bytes(core.read_bytes() + b"\n/* behaviour changed, version not bumped */")
    with pytest.raises(VerificationFailed) as err:
        deliver(store, minted.env_id, public_origin=ORIGIN, kit_dist=altered)
    assert err.value.rule == "stale_kit"
    assert minted.kit_sha256 == hashlib.sha256((kit_dist / kit_version / "core.js").read_bytes()).hexdigest()


def test_S2_the_gate_refuses_a_csp_that_is_not_first(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    db = tmp_path / "envs.db"
    store = SqliteEnvironmentStore(db)
    store.put_verified(minted)
    tag = postprocess.csp_tag(ORIGIN)
    moved = minted.html.replace(tag, "", 1).replace("</head>", tag + "</head>", 1)
    sha = html_sha256(moved)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE environments SET html = ?, html_sha256 = ?, env_id = ?",
            (moved, sha, f"reference-spring-{sha[:12]}"),
        )
    with pytest.raises(VerificationFailed) as err:
        deliver(store, f"reference-spring-{sha[:12]}", public_origin=ORIGIN, kit_dist=kit_dist)
    assert err.value.rule == "csp_mismatch"


def test_S3_KNOWN_GAP_a_hand_inserted_row_that_passes_the_cheap_checks_is_delivered(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    """Pinned, not endorsed. The gate re-hashes, re-scans and re-checks the CSP and Kit, but it does NOT re-render and the row
    carries no signature, so someone who can write the SQLite file can insert an Environment the verifier never saw. Hard
    constraint 1 therefore rests on the store being writable only by the API (single operator, D-11). Closing it (an HMAC
    attestation with a key outside the data directory, or re-rendering on delivery) is a P7 deploy-gate item. When it lands,
    flip this test to expect a refusal."""
    db = tmp_path / "envs.db"
    store = SqliteEnvironmentStore(db)
    store.put_verified(minted)
    html = postprocess.run(
        "<!doctype html><html><head></head><body><p>never rendered</p></body></html>", public_origin=ORIGIN
    )
    assert isinstance(html, str)
    sha = html_sha256(html)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE environments SET html = ?, html_sha256 = ?, env_id = ?", (html, sha, f"reference-spring-{sha[:12]}")
        )
    block = deliver(store, f"reference-spring-{sha[:12]}", public_origin=ORIGIN, kit_dist=kit_dist)
    assert block.html == html  # delivered although it was never rendered or minted


def test_N2_an_environment_must_state_a_source_even_if_the_source_is_none(kit_dist: Path) -> None:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, citations=[])
    assert (err.value.stage, err.value.rule) == ("grounding", "no_citation")


def test_N4_the_same_html_cannot_be_stored_again_under_a_different_claim(
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_verified(minted)
    same_bytes_other_title = mint(kit_dist, title="A different title")
    assert same_bytes_other_title.html_sha256 == minted.html_sha256
    with pytest.raises(ValueError, match="different metadata"):
        store.put_verified(same_bytes_other_title)


def test_N7_html_that_loads_a_different_kit_than_the_plan_says_is_refused(
    kit_dist: Path, tmp_path: Path, kit_version: str
) -> None:
    from api.verify.conftest import fixture_html

    other = tmp_path / "kit"
    shutil.copytree(kit_dist, other)
    major, minor, patch = (int(x) for x in kit_version.split("."))
    bumped = f"{major}.{minor}.{patch + 1}"
    shutil.copytree(other / kit_version, other / bumped)
    with pytest.raises(VerificationFailed) as err:
        mint(other, raw_html=fixture_html("reference-spring.html"), kit_version=bumped)
    assert (err.value.stage, err.value.rule) == ("kit", "version_mismatch")


def test_B1_the_gate_side_check_also_rejects_a_comment_before_the_csp() -> None:
    """The gate runs csp_is_first on STORED html, which may not have gone through strip_comments."""
    tag = postprocess.csp_tag(ORIGIN)
    assert not postprocess.csp_is_first(f"<!-- <head> -->\n<!doctype html><html><head>{tag}</head></html>", ORIGIN)
    assert not postprocess.csp_is_first(f"<!-- <head>\n{tag}", ORIGIN)
    assert not postprocess.csp_is_first(f"<?xml version='1.0'?><html><head>{tag}</head></html>", ORIGIN)


# ── P1: provenance (L1), grid and extremes (L2), numeric cross-check (L3), end to end through the real browser ──────────


def variant(old: str, new: str, name: str = "reference-spring.html") -> str:
    from api.verify.conftest import fixture_html

    html = fixture_html(name)
    assert old in html, f"the fixture no longer contains {old!r}"
    return html.replace(old, new, 1)


def refused(kit_dist: Path, raw_html: str, **kw) -> VerificationFailed:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, raw_html=raw_html, **kw)
    return err.value


HOOKES_PLAN = [{"id": "mechanics.hookes", "params": {"k": 50}}]


def test_L1_a_constant_wrapped_in_a_free_observable_is_ungrounded(kit_dist: Path) -> None:
    html = variant("value: extension,", "value: Synapse.observable(0.04),")
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "ungrounded_readout")


def test_L1_arithmetic_written_in_the_page_is_refused(kit_dist: Path) -> None:
    html = variant("value: extension,", "value: extension.map(function (x) { return x * 2; }),")
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "unaudited_arithmetic")


def test_L1_an_object_that_only_looks_like_an_observable_is_refused(kit_dist: Path) -> None:
    forged = "{ get: function () { return 0.04; }, set: function () {}, subscribe: function () { return function () {}; }, map: function () {} }"
    e = refused(kit_dist, variant("value: extension,", f"value: {forged},"))
    assert e.stage == "render" and e.rule in (
        "ready",
        "errors",
    )  # readout() throws, so the page never gets as far as ready


def test_L1_a_number_typed_into_a_paragraph_is_refused(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();",
        "var p = document.createElement('p'); p.textContent = 'Extension is 0.04 m'; env.stage.appendChild(p);\n  Synapse.bridge.ready();",
    )
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "unowned_number")


def test_L1_a_script_cannot_mark_its_own_element_as_kit_owned(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();",
        "var p = document.createElement('p'); p.textContent = '0.04 m'; p.setAttribute('data-synapse-owned', ''); env.stage.appendChild(p);\n  Synapse.bridge.ready();",
    )
    assert refused(kit_dist, html).rule == "unowned_number"


def test_L1_editing_the_study_note_after_it_was_made_is_refused(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();",
        "document.querySelector('.syn-note').textContent = 'The spring stretches 0.9 m.';\n  Synapse.bridge.ready();",
    )
    assert refused(kit_dist, html).rule == "owned_changed"


def test_L1_a_number_in_sanctioned_copy_must_be_backed(kit_dist: Path) -> None:
    ok = variant(
        "Synapse.bridge.ready();", "Synapse.text(env, 'The spring constant is 50 N/m.');\n  Synapse.bridge.ready();"
    )
    assert mint(kit_dist, raw_html=ok, plan_models=HOOKES_PLAN).env_id
    bad = variant(
        "Synapse.bridge.ready();", "Synapse.text(env, 'At 2 N the extension is 0.05 m.');\n  Synapse.bridge.ready();"
    )
    assert refused(kit_dist, bad).rule == "unbacked_copy_number"


def test_L1_replacing_or_redefining_the_kit_global_does_not_work(kit_dist: Path) -> None:
    redefine = variant(
        "Synapse.bridge.ready();",
        "Object.defineProperty(window, 'Synapse', { value: { audit: function () { return null; } } });\n  Synapse.bridge.ready();",
    )
    e = refused(kit_dist, redefine)
    assert e.stage == "render" and e.rule in ("errors", "ready")
    # A plain assignment is silently ignored by a non-writable property; the page keeps working with the REAL Kit and is not fooled.
    assign = variant(
        "Synapse.bridge.ready();",
        "window.Synapse = { audit: function () { return null; } };\n  Synapse.bridge.ready();",
    )
    assert mint(kit_dist, raw_html=assign, plan_models=HOOKES_PLAN).checked.models


def test_L1_the_kit_must_be_the_first_script_and_loaded_once(kit_dist: Path, kit_version: str) -> None:
    first = variant(
        f'<script src="/vendor/kit/{kit_version}/core.js"></script>',
        f'<script>window.x = 1;</script>\n<script src="/vendor/kit/{kit_version}/core.js"></script>',
    )
    e = refused(kit_dist, first)
    assert (e.stage, e.rule) == ("scan", "kit_first")
    twice = variant(
        f'<script src="/vendor/kit/{kit_version}/core.js"></script>',
        f'<script src="/vendor/kit/{kit_version}/core.js"></script>\n<script src="/vendor/kit/{kit_version}/core.js"></script>',
    )
    assert refused(kit_dist, twice).rule == "kit_first"
    assert (
        refused(kit_dist, "<!doctype html><html><head></head><body><script>1</script></body></html>").rule
        == "kit_first"
    )


@pytest.mark.parametrize(
    ("snippet", "label"),
    [
        ("var c = document.createElement('canvas'); c.getContext('2d').fillText('0.04 m', 0, 0);", "canvas"),
        ("var i = document.createElement('img'); i.src = 'data:image/png;base64,AAAA';", "image"),
        (
            "var s = document.createElement('style'); s.textContent = 'p::before { content: \"0.04 m\" }'; document.head.appendChild(s);",
            "CSS",
        ),
    ],
)
def test_L1_ways_to_show_a_number_the_dom_scan_cannot_see_are_closed_in_kit_lanes(
    kit_dist: Path, snippet: str, label: str
) -> None:
    e = refused(kit_dist, variant("Synapse.bridge.ready();", snippet + "\n  Synapse.bridge.ready();"))
    assert (e.stage, e.rule) == ("scan", "kit_lane")
    assert label.lower() in e.reason.lower()


def test_L1_the_free_lane_is_exempt_from_the_kit_lane_rules_but_gets_no_kit_layers() -> None:
    out = postprocess.run(
        "<!doctype html><html><head></head><body><canvas></canvas><script>1</script></body></html>",
        public_origin=ORIGIN,
    )
    assert isinstance(out, str)  # no kit_version given: no Kit-lane rules


def test_L3_a_changed_model_parameter_is_a_plan_mismatch(kit_dist: Path) -> None:
    html = variant("k: 50", "k: 25")
    e = refused(kit_dist, html, plan_models=HOOKES_PLAN)
    assert (e.stage, e.rule) == ("render", "plan_mismatch")
    assert "k" in e.reason and "25" in e.reason


def test_L3_a_page_that_drops_its_model_for_a_constant_is_a_plan_mismatch(kit_dist: Path) -> None:
    html = variant("value: extension,", 'value: Synapse.constant(0.04, { label: "Extension", unit: "m" }),')
    assert refused(kit_dist, html, plan_models=HOOKES_PLAN).rule == "plan_mismatch"


def test_L3_a_physics_bug_planted_in_the_kit_bundle_is_caught_by_the_independent_reference(
    kit_dist: Path, tmp_path: Path, kit_version: str
) -> None:
    """The Kit formats its own value, so its text always agrees with it; only the independent Python reference can see that the
    value is wrong. Here Hooke's law in the bundle is made 10 percent too large."""
    patched = tmp_path / "kit"
    shutil.copytree(kit_dist, patched)
    core = patched / kit_version / "core.js"
    source = core.read_text(encoding="utf-8")
    assert "fn:({load:e,k:t})=>e/t," in source
    core.write_text(source.replace("fn:({load:e,k:t})=>e/t,", "fn:({load:e,k:t})=>e/t*1.1,"), encoding="utf-8")
    e = refused(patched, variant("k: 50", "k: 50"), kit_version=kit_version)
    assert (e.stage, e.rule) == ("render", "numeric_mismatch")
    assert "independent reference" in e.reason


def test_L2_every_grid_position_and_both_extremes_are_exercised(minted: VerifiedEnvironment) -> None:
    assert minted.checked.grid_points >= 11
    assert "grid" in minted.checked.layers and "reference" in minted.checked.layers


@pytest.mark.parametrize("name", ["reference-ohm.html", "reference-pressure.html"])
def test_the_ohm_and_pressure_fixtures_are_minted_with_their_models_checked(kit_dist: Path, name: str) -> None:
    import json

    from api.verify.conftest import FIXTURES

    plan = json.loads((FIXTURES / name.replace(".html", ".plan.json")).read_text(encoding="utf-8"))
    env = mint(kit_dist, name, slug=plan["id"], title=plan["title"], plan_models=plan["models"])
    assert [m[0] for m in env.checked.models] == [m["id"] for m in plan["models"]]
    assert env.checked.reference_cases > 20


def test_ohm_with_a_constant_resistance_and_a_changed_parameter_are_both_checked(kit_dist: Path) -> None:
    """A two-control model: the sweep covers every min/mid/max combination, so a wrong value at one corner would still be found."""
    from api.verify.conftest import FIXTURES

    html = (FIXTURES / "reference-ohm.html").read_text(encoding="utf-8")
    env = mint(kit_dist, raw_html=html, slug="reference-ohm", plan_models=[{"id": "electricity.ohm", "params": {}}])
    assert env.checked.controls_exercised == 2
    assert env.checked.grid_points >= 13 + 20  # both grids, with the other control at its default


def test_L1_a_number_in_an_aria_label_is_refused(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();",
        "var p = document.createElement('p'); p.setAttribute('aria-label', 'Extension is 0.04 m'); env.stage.appendChild(p);\n  Synapse.bridge.ready();",
    )
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "unowned_attribute_number")


def test_L1_a_shadow_root_built_by_an_obfuscated_call_is_refused_at_render(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();",
        "var h = document.createElement('div'); env.stage.appendChild(h); h['attach' + 'Shadow']({ mode: 'open' }).innerHTML = '<p>0.04 m</p>';\n  Synapse.bridge.ready();",
    )
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "shadow_root")


def test_L0_shadow_dom_is_named_at_scan_in_the_kit_lanes(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();", "document.body.attachShadow({ mode: 'open' });\n  Synapse.bridge.ready();"
    )
    assert refused(kit_dist, html).stage == "scan"


def test_L1_a_number_inserted_after_the_sweep_is_still_caught(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();",
        "setTimeout(function () { var p = document.createElement('p'); p.textContent = 'Extension is 0.04 m'; env.stage.appendChild(p); }, 1200);\n  Synapse.bridge.ready();",
    )
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "unowned_number")


def test_L1_a_readout_labelled_with_the_wrong_unit_is_refused(kit_dist: Path) -> None:
    html = variant('unit: "kPa"', 'unit: "Pa"', "reference-pressure.html")
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "wrong_unit")


def test_L1_a_readout_forged_at_load_is_seen_before_any_input_redraws_it(kit_dist: Path) -> None:
    html = variant(
        "Synapse.bridge.ready();",
        "document.querySelector('[data-synapse-readout]').textContent = '0.999 m';\n  Synapse.bridge.ready();",
    )
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "readout_mismatch")


# ── core components: reset, table, graph ───────────────────────────────────────────────────────────────────────────────


OHM_GRAPH = "reference-ohm-graph.html"
OHM_PLAN = [{"id": "electricity.ohm", "params": {}}]


def test_the_graph_table_and_reset_fixture_is_minted_with_its_curve_checked(kit_dist: Path) -> None:
    e = mint(kit_dist, OHM_GRAPH, slug="reference-ohm-graph", plan_models=OHM_PLAN)
    assert e.checked.models == (("electricity.ohm", ()),)
    # one current readout, three table or graph series, and every point of the curve compared with the reference
    assert e.checked.reference_cases > 100


def test_L1_a_graph_fed_by_a_free_observable_is_ungrounded(kit_dist: Path) -> None:
    html = variant("y: current,", "y: Synapse.observable(1),", OHM_GRAPH)
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "ungrounded_readout")


def test_L1_a_graph_with_the_wrong_unit_is_refused(kit_dist: Path) -> None:
    e = refused(kit_dist, variant('yUnit: "A"', 'yUnit: "mA"', OHM_GRAPH))
    assert (e.stage, e.rule) == ("render", "wrong_unit")


def test_L1_a_table_column_with_the_wrong_unit_is_refused(kit_dist: Path) -> None:
    e = refused(kit_dist, variant('label: "Current", unit: "A"', 'label: "Current", unit: "V"', OHM_GRAPH))
    assert (e.stage, e.rule) == ("render", "wrong_unit")


def test_L1_a_button_that_only_claims_to_be_a_kit_action_is_refused(kit_dist: Path) -> None:
    html = variant(
        "Synapse.reset(env);",
        "Synapse.reset(env); var b = document.createElement('button'); b.textContent = 'Go'; b.setAttribute('data-synapse-action', 'reset'); env.controls.appendChild(b);",
        OHM_GRAPH,
    )
    e = refused(kit_dist, html)
    assert (e.stage, e.rule) == ("render", "forged_action")


def test_L1_a_plain_button_is_still_an_undeclared_control(kit_dist: Path) -> None:
    html = variant(
        "Synapse.reset(env);",
        "Synapse.reset(env); var b = document.createElement('button'); b.textContent = 'Go'; env.controls.appendChild(b);",
        OHM_GRAPH,
    )
    assert refused(kit_dist, html).rule == "undeclared_control"
