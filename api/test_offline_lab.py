"""The lab report inside an offline file and a chapter pack (W5b follow-up, D-56), in a real browser with the network closed.

The shell builds the report from what the Kit reports (`synapse_lab`). Nothing that crosses the frame boundary is trusted: only the frame the file made may speak, every
size is re-checked, and text is never inserted as markup.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, sync_playwright

from api import kitmanifest
from api.export import chapter_pack, standalone_page
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.schema.generated import Citation
from api.verify.gate import deliver
from api.verify.mint import verify_environment
from api.verify.store import SqliteEnvironmentStore

REPO = Path(__file__).resolve().parents[1]
ORIGIN = "http://localhost:3000"
PLANS = ("physics-f5-hookes_amali.json", "physics-f4-orbit.json")


@pytest.fixture(scope="module")
def inputs(kit_dist: Path, tmp_path_factory: pytest.TempPathFactory):  # noqa: ANN201
    manifest = kitmanifest.load(kit_dist, latest_version(kit_dist))
    store = SqliteEnvironmentStore(tmp_path_factory.mktemp("store") / "envs.db")
    blocks = []
    for name in PLANS:
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


def _open(html: str, tmp_path: Path, name: str, script) -> Any:  # noqa: ANN001
    path = tmp_path / name
    path.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(offline=True, viewport={"width": 360, "height": 900})
            outside: list[str] = []
            context.on("request", lambda r: outside.append(r.url) if not r.url.startswith(("file:", "about:", "data:", "blob:")) else None)
            page = context.new_page()
            page.goto(path.as_uri())
            result = script(page)
            assert outside == [], "the file asked for something outside itself"
            return result
        finally:
            browser.close()


def _ready_single(page: Page) -> None:
    page.wait_for_function("document.getElementById('state').textContent === 'Fingerprint checked.'", timeout=15000)
    page.frame_locator("#frame").locator("[data-synapse-action=record]").first.wait_for(timeout=15000)


def test_a_saved_file_shows_the_lab_report_the_student_builds(inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = inputs

    def script(page: Page) -> dict:
        _ready_single(page)
        page.wait_for_selector("#lab:not([hidden])", timeout=10000)  # the Kit reports the steps and an empty table as soon as it loads
        assert page.eval_on_selector_all("#labbody tbody tr", "rs => rs.length") == 0
        assert "No rows yet" in page.inner_text("#labbody")
        frame = page.frame_locator("#frame")
        frame.locator("[data-synapse-action=record]").first.click()
        page.wait_for_selector("#lab:not([hidden])", timeout=10000)
        page.fill("#lab-observations", "The spring got longer when I added mass.")
        text = page.eval_on_selector("#labprint", "e => e.textContent")
        return {
            "text": text,
            "rows": page.eval_on_selector_all("#labbody tbody tr", "rs => rs.length"),
            "sandbox": page.eval_on_selector("#frame", "e => e.getAttribute('sandbox')"),
            "title": blocks[0].title,
        }

    got = _open(standalone_page(blocks[0], kit_js), tmp_path, "single.html", script)
    assert got["rows"] == 1
    assert got["sandbox"] == "allow-scripts"
    assert got["text"].startswith("Lab report: " + got["title"])
    assert "Procedure" in got["text"] and "Results:" in got["text"]
    assert "The spring got longer when I added mass." in got["text"]
    assert "Conclusion\n(not written yet)" in got["text"]  # an unwritten box is said to be unwritten, never invented


def test_a_forged_or_oversize_or_markup_message_does_not_reach_the_report(inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = inputs

    def script(page: Page) -> dict:
        _ready_single(page)
        # 1) the page itself is not the frame: its own message is ignored
        page.evaluate("window.postMessage({type: 'synapse_lab', part: 'steps', steps: ['forged']}, '*')")
        page.wait_for_timeout(200)
        forged = page.eval_on_selector("#labprint", "e => e.textContent")
        frame = next(f for f in page.frames if f != page.main_frame)
        # 2) from the frame: oversize and malformed parts are refused whole
        frame.evaluate("parent.postMessage({type: 'synapse_lab', part: 'steps', steps: ['x'.repeat(301)]}, '*')")
        frame.evaluate("parent.postMessage({type: 'synapse_lab', part: 'table', caption: 'c', columns: [{label: 'a', unit: 'u'}], rows: [['1', '2']]}, '*')")
        frame.evaluate("parent.postMessage({type: 'synapse_lab', part: 'experiment', fields: [['k', 1]]}, '*')")
        page.wait_for_timeout(200)
        refused = page.eval_on_selector("#labprint", "e => e.textContent")
        # 3) markup in a valid part is shown as text, never parsed
        frame.evaluate("parent.postMessage({type: 'synapse_lab', part: 'steps', steps: ['<img src=x onerror=alert(1)>']}, '*')")
        page.wait_for_timeout(200)
        return {
            "forged": forged,
            "refused": refused,
            "images": page.eval_on_selector_all("#lab img", "i => i.length"),
            "step_text": page.eval_on_selector_all("#labbody li", "ls => ls.map(l => l.textContent)"),
        }

    got = _open(standalone_page(blocks[0], kit_js), tmp_path, "forged.html", script)
    assert "forged" not in got["forged"]
    assert "x" * 301 not in got["refused"]
    assert got["images"] == 0
    assert got["step_text"] == ["<img src=x onerror=alert(1)>"]


def test_a_chapter_pack_resets_the_report_for_each_environment(inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = inputs

    def script(page: Page) -> dict:
        page.wait_for_function("document.getElementById('state').textContent.startsWith('All')", timeout=15000)
        page.click(f'button[data-open="{blocks[0].id}"]')
        page.frame_locator("#frame").locator("[data-synapse-action=record]").first.wait_for(timeout=15000)
        page.frame_locator("#frame").locator("[data-synapse-action=record]").first.click()
        page.wait_for_selector("#lab:not([hidden])", timeout=10000)
        page.fill("#lab-conclusion", "Extension is proportional to the load.")
        first = page.eval_on_selector("#labprint", "e => e.textContent")
        page.click("#back")
        hidden_after_back = page.eval_on_selector("#lab", "e => e.hidden")
        page.click(f'button[data-open="{blocks[1].id}"]')
        page.frame_locator("#frame").locator("[data-synapse-action=record]").first.wait_for(timeout=15000)
        page.wait_for_selector("#lab:not([hidden])", timeout=10000)
        second = page.eval_on_selector("#labprint", "e => e.textContent")
        return {"first": first, "back": hidden_after_back, "second": second, "box": page.input_value("#lab-conclusion")}

    got = _open(chapter_pack("Pack", blocks, kit_js), tmp_path, "pack.html", script)
    assert "Extension is proportional to the load." in got["first"]
    assert got["back"] is True
    assert got["box"] == ""  # the first Environment's writing does not leak into the second
    assert "Extension is proportional" not in got["second"]
    assert got["second"].startswith("Lab report: " + blocks[1].title)


def test_the_shell_enforces_the_same_count_limits_as_the_web_app_and_accepts_what_sits_exactly_at_them(inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = inputs

    def script(page: Page) -> dict:
        _ready_single(page)
        frame = next(f for f in page.frames if f != page.main_frame)

        def send(message: str) -> str:
            frame.evaluate(f"parent.postMessage({message}, '*')")
            page.wait_for_timeout(150)
            return page.eval_on_selector("#labprint", "e => e.textContent")

        out = {}
        out["nine_steps"] = "step 8" in send("{type: 'synapse_lab', part: 'steps', steps: Array.from({length: 9}, (_, i) => 'step ' + i)}")
        out["eight_steps"] = "step 7" in send("{type: 'synapse_lab', part: 'steps', steps: Array.from({length: 8}, (_, i) => 'step ' + i)}")
        out["step_at_300"] = "y" * 300 in send("{type: 'synapse_lab', part: 'steps', steps: ['y'.repeat(300)]}")
        out["step_at_301"] = "z" * 301 in send("{type: 'synapse_lab', part: 'steps', steps: ['z'.repeat(301)]}")
        cols7 = "Array.from({length: 7}, (_, i) => ({label: 'c' + i, unit: 'u'}))"
        out["seven_columns"] = "c6" in send(f"{{type: 'synapse_lab', part: 'table', caption: 'seven', columns: {cols7}, rows: []}}")
        rows31 = "Array.from({length: 31}, () => ['1'])"
        out["thirty_one_rows"] = "thirty-one" in send(f"{{type: 'synapse_lab', part: 'table', caption: 'thirty-one', columns: [{{label: 'a', unit: 'u'}}], rows: {rows31}}}")
        rows30 = "Array.from({length: 30}, () => ['1'])"
        out["thirty_rows"] = "thirty" in send(f"{{type: 'synapse_lab', part: 'table', caption: 'thirty', columns: [{{label: 'a', unit: 'u'}}], rows: {rows30}}}")
        # a sparse array has holes, which survive structured cloning: it is refused, not shown as "undefined"
        out["sparse"] = "undefined" in send("{type: 'synapse_lab', part: 'steps', steps: Object.assign(new Array(3), {0: 'only the first'})}")
        out["nine_fields"] = "field 8" in send("{type: 'synapse_lab', part: 'experiment', fields: Array.from({length: 9}, (_, i) => ['name ' + i, 'field ' + i])}")
        return out

    got = _open(standalone_page(blocks[0], kit_js), tmp_path, "limits.html", script)
    assert got == {
        "nine_steps": False, "eight_steps": True, "step_at_300": True, "step_at_301": False,
        "seven_columns": False, "thirty_one_rows": False, "thirty_rows": True, "sparse": False, "nine_fields": False,
    }


def test_nothing_is_accepted_from_a_page_after_it_has_been_closed_for_a_violation(inputs, tmp_path: Path) -> None:  # noqa: ANN001
    blocks, kit_js = inputs

    def script(page: Page) -> dict:
        _ready_single(page)
        frame = next(f for f in page.frames if f != page.main_frame)
        frame.evaluate(
            "(() => { parent.postMessage({type: 'synapse_violation', problems: ['x']}, '*');"
            " parent.postMessage({type: 'synapse_lab', part: 'steps', steps: ['text from a closed page']}, '*'); })()"
        )
        page.wait_for_timeout(300)
        return {"hidden": page.eval_on_selector("#lab", "e => e.hidden"), "alert": page.inner_text("#state"), "body": page.eval_on_selector("#labprint", "e => e.textContent")}

    got = _open(standalone_page(blocks[0], kit_js), tmp_path, "violation.html", script)
    assert got["hidden"] is True and "closed" in got["alert"] and "text from a closed page" not in got["body"]
