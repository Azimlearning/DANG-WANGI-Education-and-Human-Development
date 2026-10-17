"""Real-browser smoke for the web shell (P0 task 8). Starts the real API (fakes) and the built Next.js app, then drives headless
Chromium through the whole path and prints one line per check. Exit code 1 if any check fails.

    uv run python eval/smoke/web_smoke.py            # builds the web app first
    uv run python eval/smoke/web_smoke.py --no-build

It asserts, in a real browser: the iframe's `sandbox` attribute is exactly `allow-scripts`; the slider changes the readout; a
`fetch` from inside the frame is blocked (by the CSP, with a violation as the evidence); the console has no errors before that
deliberate fetch; Peek opens to Stage and back; 360 px has no horizontal scroll and 44 px targets. Two crafted streams then prove
the host's own defences: a block with a wrong hash is never rendered, and a frame that navigates away is torn down.
Screenshots go to test-results/web-smoke/ (gitignored).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, Route, sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.kit import latest_version  # noqa: E402

SHOTS = REPO / "test-results" / "web-smoke"
API = "http://localhost:8000"
WEB = "http://localhost:3000"
TITLE = "Hooke's law: how does a spring stretch?"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)


def spawn(cmd: list[str], env: dict[str, str]) -> subprocess.Popen:
    """Start a server in its own process group so `terminate` can take down the whole tree (`pnpm start` spawns node)."""
    options: dict = {"cwd": REPO, "env": env, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    return subprocess.Popen(cmd, **options)


def terminate(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        # No process groups to signal on Windows: ask taskkill to end the process and every child it started.
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def require_free_port(port: int) -> None:
    """The smoke starts its own servers on fixed ports. If something already answers there (a server left over from an
    earlier run), `wait_http` would succeed against it and every later check would test the wrong process."""
    with socket.socket() as probe:
        probe.settimeout(0.5)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"port {port} is already in use: stop whatever is listening there and run the smoke again")


def wait_http(url: str, seconds: float = 60) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"{url} did not come up")


def sse(events: list[dict]) -> str:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events)


def crafted_block(html: str, sha: str | None = None) -> dict:
    return {
        "type": "Environment",
        "id": "crafted-1",
        "meta": {"status": "ready", "error": None},
        "title": "Crafted",
        "lane": "instantiate",
        "label": "model-checked",
        "kitVersion": "0.0.1",
        "htmlSha256": sha or hashlib.sha256(html.encode()).hexdigest(),
        "html": html,
        "citations": [{"source": "UNVERIFIED", "page": None, "quote": None, "verified": False}],
        "checked": {
            "layers": ["scan"],
            "controlsExercised": 0,
            "gridPoints": 0,
            "referenceCases": 0,
            "readouts": 0,
            "models": [],
            "limits": "A crafted block used only by the smoke test.",
        },
        "planSummary": "A crafted block used only by the smoke test.",
    }


def serve_crafted(page: Page, block: dict) -> None:
    body = sse(
        [
            {"type": "meta", "requestId": "r", "lane": "instantiate", "label": "model-checked", "kitVersion": "0.0.1"},
            {"type": "text_delta", "text": "crafted"},
            {"type": "environment", "block": block},
            {"type": "done"},
        ]
    )

    def handle(route: Route) -> None:
        if route.request.method == "OPTIONS":
            route.fulfill(
                status=204,
                headers={
                    "access-control-allow-origin": WEB,
                    "access-control-allow-methods": "POST",
                    "access-control-allow-headers": "content-type",
                },
            )
        else:
            route.fulfill(
                status=200,
                content_type="text/event-stream",
                headers={"access-control-allow-origin": WEB},
                body=body,
            )

    page.route(f"{API}/ask", handle)


def main() -> int:
    build = "--no-build" not in sys.argv
    pnpm = shutil.which("pnpm") or "pnpm"
    SHOTS.mkdir(parents=True, exist_ok=True)
    procs: list[subprocess.Popen] = []
    require_free_port(8000)
    require_free_port(3000)
    tmp = Path(tempfile.mkdtemp(prefix="synapse-smoke-"))
    try:
        # A private data directory: /ask runs the whole pipeline on fakes and verifies the Environment in a real browser.
        env = {
            **os.environ,
            "SYNAPSE_LLM_MODE": "fake",
            "DATA_DIR": str(tmp),
            "PUBLIC_ORIGIN": WEB,
            "VERIFY_INTERACTION_SECONDS": "3",
        }
        env.pop("ANTHROPIC_API_KEY", None)

        if build:
            subprocess.run([pnpm, "--filter", "web", "build"], cwd=REPO, check=True, capture_output=True)
        procs.append(spawn([sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8000"], env))
        procs.append(spawn([pnpm, "--filter", "web", "start"], env))
        wait_http(f"{API}/health")
        wait_http(WEB)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 360, "height": 780})
            page = context.new_page()
            console_errors: list[str] = []
            page_errors: list[str] = []
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: page_errors.append(str(e)))

            # ── the real path: ask, Peek, controls ──────────────────────────────────────────────────────────────────────
            page.goto(WEB)
            page.fill("#q", "Why does a spring stretch when I hang a weight on it?")
            page.click("button[type=submit]")
            # The loading skeleton is drawn from the streamed plan before the Environment is verified (D-23).
            page.wait_for_selector(f'article[aria-label="{TITLE} (draft)"]', timeout=30_000)
            check(
                "the loading skeleton appears before the Environment",
                page.query_selector("iframe") is None,
                "draft card, no frame yet",
            )
            page.wait_for_selector(f'iframe[title="{TITLE}"]', timeout=60_000)
            check(
                "the skeleton is replaced by the verified Environment",
                page.query_selector('article[aria-label$="(draft)"]') is None,
            )
            text = page.inner_text('[data-testid="answer"]')
            check("a streamed explanation appears", text.startswith("[fake:explain:"), text[:40])

            sandbox_attr = page.get_attribute("iframe", "sandbox")
            sandbox_prop = page.evaluate("document.querySelector('iframe').sandbox.value")
            allow_attr = page.get_attribute("iframe", "allow")
            check(
                "iframe sandbox attribute is exactly 'allow-scripts'",
                sandbox_attr == "allow-scripts" and sandbox_prop == "allow-scripts",
                f"{sandbox_attr!r}",
            )
            check(
                "iframe has no allow= permissions and no allow-same-origin",
                allow_attr is None and "allow-same-origin" not in (sandbox_attr or ""),
            )

            frame = page.frame_locator("iframe").first
            readout = frame.locator("[data-synapse-readout]")
            readout.wait_for(timeout=15_000)
            before = readout.inner_text()
            slider = frame.locator("input[data-synapse-control='load']")
            slider.focus()
            page.keyboard.press("End")
            page.wait_for_timeout(300)
            after = readout.inner_text()
            check("moving the slider changes the readout", before != after, f"{before!r} -> {after!r}")
            check("readout is the Hooke's law value at 10 N and 50 N/m", after.strip() == "0.200 m", after)

            kit_loaded = page.evaluate(
                "v => fetch('/vendor/kit/' + v + '/core.js').then(r => r.status)",
                latest_version(REPO / "packages" / "kit" / "dist"),
            )
            check("the Kit is same-origin through the /vendor rewrite", kit_loaded == 200, str(kit_loaded))
            page.screenshot(path=str(SHOTS / "01-peek-360.png"), full_page=True)

            # ── phone-first: 360 px wide, 44 px targets ────────────────────────────────────────────────────────────────
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check("no horizontal scroll at 360 px", overflow <= 0, f"{overflow}px")
            heights = page.evaluate(
                "[...document.querySelectorAll('button, input')].map(e => Math.round(e.getBoundingClientRect().height))"
            )
            check("every page-level control is at least 44 px tall", all(h >= 44 for h in heights), str(heights))

            # ── Provenance is visible ──────────────────────────────────────────────────────────────────────────────────
            body = page.inner_text("body")
            check(
                "provenance shows label, lane, source and limits",
                all(
                    s in body
                    for s in (
                        "Checked by code",
                        "Compose",
                        "Source:",
                        "What was checked",
                        "Limits:",
                        "not verified",
                    )
                ),
            )

            # ── A concept-check answer is remembered on this device only ───────────────────────────────────────────────────────────
            choices = page.frame_locator("iframe").first.locator("[data-synapse-action=choose]")
            if choices.count() > 0:
                choices.first.click()
                page.wait_for_function(
                    "[...document.querySelectorAll('summary')].some(s => s.textContent.includes('My progress (1)'))",
                    timeout=5000,
                )
                stored = page.evaluate("localStorage.getItem('synapse.progress.v1')")
                check(
                    "the first concept-check answer is kept in this browser's storage and counted in My progress",
                    bool(stored) and '"tries":1' in stored,
                )
            else:
                check("the Environment has a concept check to answer", False)

            # ── A shared link opens the stored Environment through the gate ───────────────────────────────────────────────────────────
            import json as _json
            import urllib.request as _url

            with _url.urlopen(f"{API}/library", timeout=10) as resp:  # noqa: S310 - our own local API
                stored = _json.loads(resp.read())["environments"]
            if stored:
                shared = page.context.new_page()
                shared.goto(f"{WEB}/e/{stored[0]['id']}")
                shared.wait_for_selector("iframe", timeout=20000)
                sandbox = shared.eval_on_selector("iframe", "e => e.getAttribute('sandbox')")
                body_text = shared.inner_text("body")
                copy_h = shared.eval_on_selector(
                    "button:has-text('Copy link')", "e => Math.round(e.getBoundingClientRect().height)"
                )
                check(
                    "a shared link shows the Environment in the exact sandbox with its provenance and a 44 px copy button",
                    sandbox == "allow-scripts" and "Source:" in body_text and copy_h >= 44,
                    f"sandbox={sandbox} copy_h={copy_h}",
                )
                shared.goto(f"{WEB}/e/not-a-real-environment-000000000000")
                shared.wait_for_selector("[role=alert]", timeout=10000)
                check("a link to nothing says so and shows no frame", shared.query_selector("iframe") is None)
                shared.close()
            else:
                check("the library holds the Environment that was just made", False)

            # ── Stage ─────────────────────────────────────────────────────────────────────────────────────────────────
            page.click("button:has-text('Open')")
            page.wait_for_selector("[role=dialog]")
            stage_sandbox = page.get_attribute("[role=dialog] iframe", "sandbox")
            check(
                "Stage opens full viewport with the same exact sandbox",
                stage_sandbox == "allow-scripts",
                f"{stage_sandbox!r}",
            )
            page.screenshot(path=str(SHOTS / "02-stage-360.png"))
            page.keyboard.press("Escape")
            page.wait_for_selector("[role=dialog]", state="detached")
            check("Escape returns from Stage to Peek", page.locator("article").count() == 1)

            errors_before_fetch = list(console_errors) + list(page_errors)
            check(
                "no console errors and no page errors so far",
                not errors_before_fetch,
                "; ".join(errors_before_fetch)[:200],
            )

            # ── a fetch from inside the frame is blocked ───────────────────────────────────────────────────────────────
            frame_obj = next(f for f in page.frames if f != page.main_frame)
            outcome = frame_obj.evaluate(
                "fetch('" + API + "/health').then(() => 'ALLOWED', (e) => 'blocked: ' + e.name)"
            )
            page.wait_for_timeout(300)
            violation = [m for m in console_errors if "Content Security Policy" in m]
            check("a fetch from inside the frame is blocked", outcome.startswith("blocked"), outcome)
            check(
                "the block is the CSP's doing (a violation was reported)",
                bool(violation),
                (violation[0][:90] if violation else "none"),
            )

            # ── the host's own defences, on crafted streams ───────────────────────────────────────────────────────────
            page.unroute_all()
            wrong = context.new_page()
            serve_crafted(wrong, crafted_block("<!doctype html><p>tampered</p>", sha="0" * 64))
            wrong.goto(WEB)
            wrong.fill("#q", "x")
            wrong.click("button[type=submit]")
            wrong.wait_for_selector("main [role=alert]", timeout=10_000)
            check(
                "a block with a wrong hash is never rendered",
                wrong.locator("iframe").count() == 0,
                wrong.inner_text("main [role=alert]")[:70],
            )

            nav = context.new_page()
            navigating = "<!doctype html><html><body><p>hi</p><script>setTimeout(function(){window['loc'+'ation']='/vendor/kit/0.0.1/manifest.json'},200)</script></body></html>"
            serve_crafted(nav, crafted_block(navigating))
            nav.goto(WEB)
            nav.fill("#q", "x")
            nav.click("button[type=submit]")
            nav.wait_for_selector("iframe", timeout=10_000)
            # Not "[role=alert]": Next.js has its own empty route announcer with that role, which would match at once.
            nav.wait_for_selector("main [role=alert]", timeout=10_000)
            nav.wait_for_selector("iframe", state="detached", timeout=10_000)
            if os.environ.get("SMOKE_DEBUG"):
                print("DEBUG iframes:", nav.locator("iframe").count(), "| main:", nav.inner_html("main")[:500])
            check(
                "a frame that navigates away is torn down by the host",
                nav.locator("iframe").count() == 0,
                nav.inner_text("main [role=alert]")[:70],
            )
            browser.close()
    finally:
        for proc in procs:
            terminate(proc)
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
