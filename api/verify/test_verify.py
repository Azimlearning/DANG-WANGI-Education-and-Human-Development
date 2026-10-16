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
        label="dev-fixture",
        kit_version="0.0.1",
        citations=[Citation(source="UNVERIFIED (corpus not loaded until P2)", page=None, quote=None, verified=False)],
        plan_summary="A hand-written fixture.",
        public_origin=ORIGIN,
        kit_dist=kit_dist,
    )


def test_good_fixture_is_minted_with_what_was_checked(minted: VerifiedEnvironment) -> None:
    assert minted.label == "dev-fixture"
    assert minted.checked.layers == ("postprocess", "scan", "render")
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
    assert block.label == "dev-fixture"
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


def test_bad_bypass_is_NOT_caught_yet_and_that_gap_is_documented(kit_dist: Path) -> None:
    """A hand-written wrong number in a readout moves with the slider, so the render layer cannot see it. Catching it is L1 (P1).
    When L1 lands this test must be flipped to expect a refusal; until then it pins the honest state: P0 does not detect it."""
    minted = mint(kit_dist, "reference-spring.bad-bypass.html")
    assert (
        minted.label == "dev-fixture"
    )  # the only label reachable today, and the one that promises nothing about correctness


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
        ("model-checked", "unreachable"),
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
    minted: VerifiedEnvironment, tmp_path: Path, kit_dist: Path
) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    store.put_verified(minted)
    altered = tmp_path / "kit"
    shutil.copytree(kit_dist, altered)
    core = altered / "0.0.1" / "core.js"
    core.write_bytes(core.read_bytes() + b"\n/* behaviour changed, version not bumped */")
    with pytest.raises(VerificationFailed) as err:
        deliver(store, minted.env_id, public_origin=ORIGIN, kit_dist=altered)
    assert err.value.rule == "stale_kit"
    assert minted.kit_sha256 == hashlib.sha256((kit_dist / "0.0.1" / "core.js").read_bytes()).hexdigest()


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


def test_N7_html_that_loads_a_different_kit_than_the_plan_says_is_refused(kit_dist: Path, tmp_path: Path) -> None:
    from api.verify.conftest import fixture_html

    other = tmp_path / "kit"
    shutil.copytree(kit_dist, other)
    shutil.copytree(other / "0.0.1", other / "0.0.2")
    with pytest.raises(VerificationFailed) as err:
        mint(other, raw_html=fixture_html("reference-spring.html"), kit_version="0.0.2")
    assert (err.value.stage, err.value.rule) == ("kit", "version_mismatch")


def test_B1_the_gate_side_check_also_rejects_a_comment_before_the_csp() -> None:
    """The gate runs csp_is_first on STORED html, which may not have gone through strip_comments."""
    tag = postprocess.csp_tag(ORIGIN)
    assert not postprocess.csp_is_first(f"<!-- <head> -->\n<!doctype html><html><head>{tag}</head></html>", ORIGIN)
    assert not postprocess.csp_is_first(f"<!-- <head>\n{tag}", ORIGIN)
    assert not postprocess.csp_is_first(f"<?xml version='1.0'?><html><head>{tag}</head></html>", ORIGIN)
