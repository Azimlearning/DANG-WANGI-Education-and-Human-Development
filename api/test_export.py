"""The offline single-file export, in a real browser with the network closed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from api import kitmanifest
from api.export import ExportRefused, standalone_page
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.schema.generated import Citation
from api.verify.gate import deliver
from api.verify.mint import verify_environment
from api.verify.store import SqliteEnvironmentStore

REPO = Path(__file__).resolve().parents[1]
ORIGIN = "http://localhost:3000"


@pytest.fixture(scope="module")
def exported(kit_dist: Path, tmp_path_factory: pytest.TempPathFactory):  # noqa: ANN201
    manifest = kitmanifest.load(kit_dist, latest_version(kit_dist))
    plan = plan_module.parse((REPO / "data" / "plans" / "physics-f5-ohm_explorer.json").read_text(encoding="utf-8"))
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
    store = SqliteEnvironmentStore(tmp_path_factory.mktemp("store") / "envs.db")
    store.put_verified(env)
    block = deliver(store, env.env_id, public_origin=ORIGIN, kit_dist=kit_dist)
    kit_js = (kit_dist / block.kitVersion / "core.js").read_bytes()
    return block, kit_js


def open_offline(page_html: str, tmp_path: Path, mutate=None):  # noqa: ANN001, ANN201
    """Open the file from disk with every network request aborted; return (state text, readout texts, request log)."""
    path = tmp_path / "export.html"
    path.write_text(page_html, encoding="utf-8")
    requests: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": 360, "height": 800})

            def block_all(route) -> None:  # noqa: ANN001
                url = route.request.url
                if not url.startswith(("file:", "about:", "data:")):
                    requests.append(url)
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", block_all)
            page = context.new_page()
            page.goto(path.as_uri())
            page.wait_for_function(
                "document.getElementById('state').textContent !== 'Checking this file before it runs.'", timeout=10000
            )
            state = page.inner_text("#state")
            readouts: list[str] = []
            moved = False
            if page.query_selector("#frame:not([hidden])"):
                frame = page.frame_locator("#frame")
                frame.locator("[data-synapse-control]").first.wait_for(timeout=10000)
                before = frame.locator("[data-synapse-readout]").all_inner_texts()
                frame.locator("input[type=range]").first.evaluate(
                    "e => { e.value = e.max; e.dispatchEvent(new Event('input', {bubbles: true})); }"
                )
                page.wait_for_timeout(300)
                readouts = frame.locator("[data-synapse-readout]").all_inner_texts()
                moved = readouts != before
                sandbox = page.eval_on_selector("#frame", "e => e.getAttribute('sandbox')")
                return state, readouts, requests, moved, sandbox
            return state, readouts, requests, moved, None
        finally:
            browser.close()


def test_the_exported_file_runs_offline_in_the_exact_sandbox_and_a_slider_moves_a_readout(
    exported, tmp_path: Path
) -> None:  # noqa: ANN001
    block, kit_js = exported
    state, readouts, requests, moved, sandbox = open_offline(standalone_page(block, kit_js), tmp_path)
    assert state == "Fingerprint checked." and moved and readouts
    assert sandbox == "allow-scripts"  # and nothing else
    assert requests == []  # no network request was even attempted


def test_the_file_states_its_provenance_and_limits(exported) -> None:  # noqa: ANN001
    block, kit_js = exported
    page = standalone_page(block, kit_js)
    for needle in (
        "Checked by code, no verified textbook source",
        "not verified",
        "Limits:",
        "What was checked:",
        block.id,
        "saved copy",
    ):
        assert needle in page
    wrapper = re.sub(
        r"var PAYLOAD = .*?;\n", "", page, flags=re.DOTALL
    )  # the Environment's own CSP text inside the payload names its origin
    assert not re.search(r"https?://", wrapper), "the wrapper must not point anywhere"


def test_a_changed_page_or_changed_kit_in_the_file_is_not_run(exported, tmp_path: Path) -> None:  # noqa: ANN001
    block, kit_js = exported
    good = standalone_page(block, kit_js)
    # Edit the Environment's text inside the payload without touching the recorded fingerprint.
    tampered = good.replace("Voltage", "Voltagf", 1)
    assert tampered != good
    state, readouts, requests, moved, _ = open_offline(tampered, tmp_path)
    assert "does not match the fingerprint" in state and readouts == [] and not moved
    # Same for the Kit bytes: change them inside the payload and leave the recorded fingerprint alone.
    kit_marker = '"kit": "'
    assert kit_marker in good
    state2, *_ = open_offline(good.replace(kit_marker, kit_marker + "//", 1), tmp_path)
    assert "does not match the fingerprint" in state2


def test_a_hostile_title_or_placeholder_text_cannot_break_the_file(exported) -> None:  # noqa: ANN001
    block, kit_js = exported
    hostile = block.model_copy(
        update={"title": "</title><script>alert(1)</script> __PAYLOAD__ __EXPECT__", "planSummary": "<b>x</b> __ID__"}
    )
    page = standalone_page(hostile, kit_js)
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert page.count("var PAYLOAD = ") == 1 and "<b>x</b>" not in page


def test_the_export_refuses_a_page_without_the_expected_kit_tag_or_with_a_wrong_hash(exported) -> None:  # noqa: ANN001
    block, kit_js = exported
    with pytest.raises(ExportRefused):
        standalone_page(block.model_copy(update={"kitVersion": "9.9.9"}), kit_js)
    with pytest.raises(ExportRefused):
        standalone_page(block.model_copy(update={"htmlSha256": "0" * 64}), kit_js)
    with pytest.raises(ExportRefused):
        standalone_page(block, kit_js + b"</script>")
