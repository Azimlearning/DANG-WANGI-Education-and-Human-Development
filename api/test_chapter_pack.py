"""The chapter pack: several Environments in one offline file, in a real browser with the network closed (W6, D-49)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from api import kitmanifest
from api.export import ExportRefused, chapter_pack
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
def pack_inputs(kit_dist: Path, tmp_path_factory: pytest.TempPathFactory):  # noqa: ANN201
    manifest = kitmanifest.load(kit_dist, latest_version(kit_dist))
    store = SqliteEnvironmentStore(tmp_path_factory.mktemp("store") / "envs.db")
    blocks = []
    for name in ("physics-f5-ohm_explorer.json", "physics-f5-pressure_depth.json"):
        plan = plan_module.parse((REPO / "data" / "plans" / name).read_text(encoding="utf-8"))
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
        store.put_verified(env)
        blocks.append(deliver(store, env.env_id, public_origin=ORIGIN, kit_dist=kit_dist))
    return blocks, (kit_dist / blocks[0].kitVersion / "core.js").read_bytes()


def run_pack(html: str, tmp_path: Path, script):  # noqa: ANN001, ANN201
    path = tmp_path / "pack.html"
    path.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(offline=True)
            requests: list[str] = []
            context.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("file:", "about:", "data:", "blob:")) else None)
            page = context.new_page()
            page.goto(path.as_uri())
            page.wait_for_function("document.getElementById('state').textContent !== 'Checking this file before anything runs.'", timeout=15000)
            return script(page), requests
        finally:
            browser.close()


def test_every_fingerprint_is_checked_and_each_environment_opens_in_the_exact_sandbox(pack_inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = pack_inputs

    def script(page):  # noqa: ANN001, ANN202
        out = {"state": page.inner_text("#state"), "enabled": page.locator("button[data-open]:not([disabled])").count()}
        page.click(f'button[data-open="{blocks[0].id}"]')
        page.wait_for_selector("#frame[srcdoc]", timeout=5000)
        out["sandbox"] = page.get_attribute("#frame", "sandbox")
        out["visible_prov"] = page.locator("section.prov:not([hidden])").count()
        frame = page.frame_locator("#frame")
        before = frame.locator("[data-synapse-readout]").all_inner_texts()
        frame.locator("input[data-synapse-control]").first.focus()
        page.keyboard.press("End")
        page.wait_for_timeout(300)
        out["moved"] = frame.locator("[data-synapse-readout]").all_inner_texts() != before
        page.click("#back")
        out["back"] = (page.locator("#list").is_visible(), page.get_attribute("#frame", "srcdoc"))
        return out

    out, requests = run_pack(chapter_pack("Physics Form 5", blocks, kit_js), tmp_path, script)
    assert out["state"] == "All 2 fingerprints checked." and out["enabled"] == 2
    assert out["sandbox"] == "allow-scripts" and out["visible_prov"] == 1 and out["moved"]
    assert out["back"] == (True, None)
    assert requests == []


def test_a_tampered_environment_is_not_run_and_the_others_still_open(pack_inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = pack_inputs
    good = chapter_pack("Physics Form 5", blocks, kit_js)
    # The last "Voltage" is inside an Environment's data; the first can sit in the Kit script (the transformer model has one), which would stop every Environment.
    at = good.rindex("Voltage")
    tampered = good[:at] + "Voltagf" + good[at + len("Voltage"):]
    assert tampered != good

    def script(page):  # noqa: ANN001, ANN202
        return {
            "state": page.inner_text("#state"),
            "enabled": page.locator("button[data-open]:not([disabled])").count(),
            "texts": page.locator("button[data-open]").all_inner_texts(),
        }

    out, _ = run_pack(tampered, tmp_path, script)
    assert "1 of 2" in out["state"] and out["enabled"] == 1
    assert any("Not run" in t for t in out["texts"])


def test_a_changed_kit_stops_every_environment(pack_inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = pack_inputs
    good = chapter_pack("Physics Form 5", blocks, kit_js)
    marker = '"kit": "'
    out, _ = run_pack(good.replace(marker, marker + "//", 1), tmp_path, lambda page: page.locator("button[data-open]:not([disabled])").count())
    assert out == 0


def test_the_file_wraps_nothing_from_another_origin_and_states_provenance(pack_inputs) -> None:  # noqa: ANN001
    blocks, kit_js = pack_inputs
    page = chapter_pack("Physics Form 5", blocks, kit_js)
    wrapper = re.sub(r"var PAYLOAD = .*?;\n", "", page, flags=re.DOTALL)
    assert not re.search(r"https?://", wrapper)
    for needle in ("Limits:", "What was checked:", "saved copy", "Checked by code, no verified textbook source", blocks[0].id, blocks[1].id):
        assert needle in page


def test_a_pack_that_cannot_be_made_safely_is_refused(pack_inputs) -> None:  # noqa: ANN001
    blocks, kit_js = pack_inputs
    with pytest.raises(ExportRefused, match="at least one"):
        chapter_pack("x", [], kit_js)
    with pytest.raises(ExportRefused, match="twice"):
        chapter_pack("x", [blocks[0], blocks[0]], kit_js)
    other = blocks[1].model_copy(update={"kitVersion": "9.9.9"})
    with pytest.raises(ExportRefused, match="different Kits"):
        chapter_pack("x", [blocks[0], other], kit_js)
    changed = blocks[1].model_copy(update={"html": blocks[1].html + " "})
    with pytest.raises(ExportRefused, match="recorded hash"):
        chapter_pack("x", [blocks[0], changed], kit_js)
    with pytest.raises(ExportRefused, match="script element"):
        chapter_pack("x", blocks, kit_js + b"</script>")
