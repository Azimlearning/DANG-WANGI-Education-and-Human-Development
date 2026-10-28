"""Real-browser smoke for Bahasa Melayu (W12, D-62). One lab is built in English and Malay into a private store, the API runs with drafts shown and the web app is built with
`NEXT_PUBLIC_BM_DRAFTS=1`, and headless Chromium switches the language.

    uv run python eval/smoke/bm_smoke.py            # builds the web app first (with drafts on)
    uv run python eval/smoke/bm_smoke.py --no-build

It asserts, in a real browser: asking an Ohm's law question opens the English lab from the library; the BM switch flips the page's own words (Paparkan, Kongsi, Luar talian)
and the lab itself (a Malay title and a Malay document language) while the sandbox stays exactly `allow-scripts`; the draft mark is on screen; the Malay lab's slider still
moves its readout; EN returns the English lab; and at 360 px nothing overflows and every control is 44 px.

The web build is made WITH drafts on, so run `uv run python eval/smoke/web_smoke.py` (which rebuilds) afterwards, not with `--no-build`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.core.settings import Settings  # noqa: E402
from api.i18n import overlay  # noqa: E402
from api.pipeline import library  # noqa: E402
from api.seed import open_store  # noqa: E402
from eval.smoke.web_smoke import RESULTS, SHOTS, check, require_free_port, spawn, terminate, wait_http  # noqa: E402

API_PORT = int(os.environ.get("SMOKE_API_PORT", "8021"))
WEB_PORT = int(os.environ.get("SMOKE_WEB_PORT", "3021"))
API = f"http://localhost:{API_PORT}"
WEB = f"http://localhost:{WEB_PORT}"
QUESTION = "What happens to the current if I raise the resistance in a circuit?"
ENGLISH_TITLE = "Ohm's law: current, voltage and resistance"
MALAY_TITLE = "Hukum Ohm: arus, beza keupayaan dan rintangan"


def main() -> int:
    build = "--no-build" not in sys.argv
    pnpm = shutil.which("pnpm") or "pnpm"
    SHOTS.mkdir(parents=True, exist_ok=True)
    require_free_port(API_PORT)
    require_free_port(WEB_PORT)
    tmp = Path(tempfile.mkdtemp(prefix="synapse-bm-smoke-"))
    procs: list[subprocess.Popen] = []
    try:
        kit = REPO / "packages" / "kit" / "dist"
        settings = Settings(_env_file=None, data_dir=tmp, kit_dist_dir=kit, public_origin=WEB)  # type: ignore[call-arg]
        library.seed(open_store(settings), kit_dist=kit, public_origin=WEB, interaction_seconds=1.0, only={"ohm_explorer"}, translations_dir=overlay.OVERLAYS)

        env = {
            **os.environ,
            "SYNAPSE_LLM_MODE": "fake",
            "DATA_DIR": str(tmp),
            "PUBLIC_ORIGIN": WEB,
            "NEXT_PUBLIC_API_BASE_URL": API,
            "NEXT_PUBLIC_BM_DRAFTS": "1",
            "BM_SHOW_DRAFTS": "true",
            "VERIFY_INTERACTION_SECONDS": "3",
            "KIT_DIST_DIR": str(kit),
        }
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CORPUS_DIR", None)
        if build:
            subprocess.run([pnpm, "--filter", "web", "build"], cwd=REPO, env=env, check=True, capture_output=True)
        procs.append(spawn([sys.executable, "-m", "uvicorn", "api.main:app", "--app-dir", str(REPO), "--port", str(API_PORT)], env, cwd=tmp))
        procs.append(spawn([pnpm, "--filter", "web", "exec", "next", "start", "--port", str(WEB_PORT)], env))
        wait_http(f"{API}/health")
        wait_http(WEB)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            console_errors: list[str] = []
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

            page.goto(WEB)
            page.fill("#q", QUESTION)
            page.click("button[type=submit]")
            page.wait_for_selector(f'iframe[title="{ENGLISH_TITLE}"]', timeout=60_000)
            check("an Ohm's law question opens the English lab from the library", True)
            check("the page starts in English", page.inner_text("body").count("Present") >= 1 and page.evaluate("document.documentElement.lang") == "en")

            page.get_by_role("button", name="BM").first.click()
            page.wait_for_selector(f'iframe[title="{MALAY_TITLE}"]', timeout=60_000)
            check("BM flips the lab to its Malay Environment", True)
            body = page.inner_text("body")
            check("the page's own words are Malay (Paparkan, Kongsi, Luar talian)", all(w in body for w in ("Paparkan", "Kongsi", "Luar talian")))
            check("the draft mark is on screen", "Draf terjemahan" in body)
            check("the page's document language is ms", page.evaluate("document.documentElement.lang") == "ms")
            frame = page.frame_locator("iframe").first
            frame.locator("h1").wait_for(timeout=15_000)
            check("the lab's own title is Malay", frame.locator("h1").inner_text() == MALAY_TITLE, frame.locator("h1").inner_text())
            check("the lab's document language is ms", frame.locator("html").get_attribute("lang") == "ms")
            check("the Kit's own words are Malay (Cuba ini, Idea utama)", "Cuba ini:" in frame.locator("body").inner_text() and "Idea utama:" in frame.locator("body").inner_text())
            sandbox = page.get_attribute("iframe", "sandbox")
            check("the Malay lab is sandboxed exactly like the English one", sandbox == "allow-scripts", f"{sandbox!r}")

            readout = frame.locator("[data-synapse-readout]").first
            readout.wait_for(timeout=15_000)
            before = readout.inner_text()
            slider = frame.locator("input[data-synapse-control]").first
            slider.focus()
            page.keyboard.press("End")
            page.wait_for_timeout(300)
            check("the Malay lab's slider moves its readout", readout.inner_text() != before, f"{before!r} -> {readout.inner_text()!r}")
            page.screenshot(path=str(SHOTS / "bm-01-lab-1280.png"))

            page.get_by_role("button", name="EN").first.click()
            page.wait_for_selector(f'iframe[title="{ENGLISH_TITLE}"]', timeout=30_000)
            check("EN returns the English lab", page.evaluate("document.documentElement.lang") == "en")

            page.set_viewport_size({"width": 360, "height": 780})
            page.get_by_role("button", name="BM").first.click()
            page.wait_for_selector(f'iframe[title="{MALAY_TITLE}"]', timeout=60_000)
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check("no horizontal scroll at 360 px in Malay", overflow <= 0, f"{overflow}px")
            heights = page.evaluate("[...document.querySelectorAll('button, input')].filter(e => e.getClientRects().length > 0).map(e => Math.round(e.getBoundingClientRect().height))")
            check("every visible control is at least 44 px tall in Malay", all(h >= 44 for h in heights), str(heights))
            page.screenshot(path=str(SHOTS / "bm-02-lab-360.png"), full_page=True)
            check("the console has no errors", not console_errors, "; ".join(console_errors)[:200])
            browser.close()
    finally:
        for proc in procs:
            terminate(proc)
        shutil.rmtree(tmp, ignore_errors=True)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
