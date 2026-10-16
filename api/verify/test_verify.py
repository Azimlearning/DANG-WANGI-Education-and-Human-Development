"""The trust path end to end: the good fixture is minted, stored and delivered; each planted defect is refused at its named
layer; a stored Environment changed by one byte is refused; the mint cannot be used outside the verifier."""

from __future__ import annotations

import copy
import pickle
import re
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


def test_a_verified_environment_cannot_be_subclassed_changed_copied_or_pickled(minted: VerifiedEnvironment) -> None:
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


def test_the_store_refuses_anything_that_is_not_a_verified_environment(tmp_path: Path) -> None:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    with pytest.raises(TypeError):
        store.put_verified({"env_id": "x"})  # type: ignore[arg-type]


def test_the_mint_issuer_and_constructor_appear_only_in_the_verifier_source() -> None:
    """Source scan: `_issue` is referenced only in api/verify/mint.py, and `VerifiedEnvironment(` is constructed nowhere else.
    Test files may construct it to prove it refuses; this file is excluded because it names the strings it looks for."""
    offenders: list[str] = []
    this_file = Path(__file__).resolve()
    for path in sorted((REPO / "api").rglob("*.py")):
        if path.resolve() in (this_file, REPO / "api" / "verify" / "mint.py"):
            continue
        text = path.read_text(encoding="utf-8")
        is_test = path.name.startswith("test_") or path.name == "conftest.py"
        if re.search(r"\b_issue\b", text):
            offenders.append(f"{path.relative_to(REPO)}: _issue")
        if not is_test and re.search(r"\bVerifiedEnvironment\s*\(", text):
            offenders.append(f"{path.relative_to(REPO)}: VerifiedEnvironment(")
    assert offenders == []


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
