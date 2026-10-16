# Ported from Azimlearning/GenUI-Education, Synapse-V3/evals/render_check.py (monorepo @ 835a2ce, v3 as of 2026-08) and
# docs/EVALS.md section 4. Read in full and adapted. Kept: the production-shaped harness (an iframe with sandbox="allow-scripts"
# and srcdoc inside a parent that listens for bridge messages) and the ready, control-wiring and no-errors assertions. Changed:
# wiring is judged by the declared readouts changing (not a screenshot diff, which a control's own label can satisfy), the
# network is closed except the Kit, the scripted interaction is time-boxed, and 360 px width and 44 px touch targets are checked.
"""The render harness (verification layer "render"): runs the Environment in headless Chromium the way the web app will.

It asserts: `synapse_ready` within 5 s; every declared control (`[data-synapse-control]`) changes at least one declared readout
(`[data-synapse-readout]`) within 1 s; no uncaught exception, console error or blocked request during a scripted interaction;
no horizontal overflow at 360 px; touch targets of at least 44 px. Anything else is a refusal that names the rule, and the control.

Sync Playwright is used on purpose: call this from a thread (`asyncio.to_thread`) when inside an event loop.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Route, sync_playwright

READY_TIMEOUT_MS = 5_000
CONTROL_WIRE_TIMEOUT_MS = 1_000
INTERACTION_SECONDS = 10.0
MIN_TOUCH_TARGET_PX = 44
PHONE_WIDTH_PX = 360

HARNESS = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">
<script>
  window.__synapse = { ready: false, errors: [], events: [] };
  window.addEventListener("message", function (e) {
    var frame = document.getElementById("artifact");
    if (e.source !== frame.contentWindow) return;
    var d = e.data || {};
    if (d.type === "synapse_ready") window.__synapse.ready = true;
    if (d.type === "synapse_error") window.__synapse.errors.push(String(d.message));
    if (d.type === "synapse_event") window.__synapse.events.push(d);
  });
</script>
<iframe id="artifact" sandbox="allow-scripts" style="width:__WIDTH__px;height:640px;border:0"></iframe>
<script>document.getElementById("artifact").srcdoc = __ARTIFACT_HTML__;</script>
</body></html>"""


@dataclass
class ControlResult:
    id: str
    wired: bool = False
    stable: bool = True
    height_px: float = 0.0


@dataclass
class RenderReport:
    ready: bool = False
    controls: list[ControlResult] = field(default_factory=list)
    readouts: int = 0
    undeclared_controls: list[str] = field(default_factory=list)
    duplicate_controls: list[str] = field(default_factory=list)
    a11y_problems: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    artifact_errors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    blocked_requests: list[str] = field(default_factory=list)
    navigations: list[str] = field(default_factory=list)
    overflow_px: float = 0.0
    interaction_seconds: float = 0.0
    harness_error: str = ""

    def refusal(self, require_controls: bool = True) -> tuple[str, str] | None:
        """The first failed rule as (rule, reason), or None when the Environment passed."""
        if not self.ready:
            return ("ready", f"synapse_ready was not received within {READY_TIMEOUT_MS} ms")
        if self.navigations:
            return ("navigation", "the frame navigated away: " + self.navigations[0][:200])
        if self.harness_error:
            # Fail closed: the harness lost the page (for example the frame navigated and its context was destroyed).
            rule = "navigation" if "navigation" in self.harness_error.lower() else "harness_error"
            return (rule, "the harness could not finish: " + self.harness_error[:200])
        if self.undeclared_controls:
            return (
                "undeclared_control",
                f"interactive element {self.undeclared_controls[0]} is not a declared control ([data-synapse-control])",
            )
        if self.duplicate_controls:
            return ("duplicate_control", f"control id '{self.duplicate_controls[0]}' is declared more than once")
        if require_controls and not self.controls:
            return ("no_controls", "no declared control found ([data-synapse-control])")
        for c in self.controls:
            if not c.wired:
                return (
                    "dead_control",
                    f"control '{c.id}' changed no declared readout within {CONTROL_WIRE_TIMEOUT_MS} ms",
                )
        for c in self.controls:
            if not c.stable:
                return (
                    "unstable_readout",
                    f"readouts changed without input or did not return to the same values around control '{c.id}'",
                )
        if self.a11y_problems:
            return ("a11y", self.a11y_problems[0])
        for c in self.controls:
            if c.height_px < MIN_TOUCH_TARGET_PX:
                return (
                    "touch_target",
                    f"control '{c.id}' is {c.height_px:.0f} px tall (minimum {MIN_TOUCH_TARGET_PX})",
                )
        if self.overflow_px > 0:
            return ("horizontal_overflow", f"content is {self.overflow_px:.0f} px wider than {PHONE_WIDTH_PX} px")
        errors = self.page_errors + self.artifact_errors + self.console_errors
        if errors:
            return ("errors", "runtime error: " + errors[0][:200])
        if self.blocked_requests:
            return ("blocked_request", "tried to load: " + self.blocked_requests[0][:200])
        return None


def _kit_file(kit_dist: Path, url_path: str) -> Path | None:
    """`/vendor/kit/0.0.1/core.js` to `<kit_dist>/0.0.1/core.js`; None for anything that escapes the folder."""
    relative = url_path.removeprefix("/vendor/kit/")
    candidate = (kit_dist / relative).resolve()
    if kit_dist.resolve() not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def render_check(
    html: str,
    *,
    kit_dist: Path,
    public_origin: str,
    require_controls: bool = True,
    interaction_seconds: float = INTERACTION_SECONDS,
) -> RenderReport:
    """Run `html` in headless Chromium. `html` is the post-processed document (it carries our CSP)."""
    report = RenderReport()
    origin = public_origin.rstrip("/")
    harness_url = f"{origin}/__harness__"

    # `</` must be escaped or the Environment's own </script> closes the harness script mid-string.
    payload = json.dumps(html).replace("</", "<\\/")
    harness = HARNESS.replace("__ARTIFACT_HTML__", payload).replace("__WIDTH__", str(PHONE_WIDTH_PX))

    def handle(route: Route) -> None:
        url = route.request.url
        parsed = urlparse(url)
        if url == harness_url:
            route.fulfill(content_type="text/html", body=harness)
        elif url.startswith(f"{origin}/vendor/kit/"):
            file = _kit_file(kit_dist, parsed.path)
            if file is None:
                report.blocked_requests.append(url)
                route.fulfill(status=404, body="not found")
            else:
                route.fulfill(content_type="application/javascript", body=file.read_bytes())
        else:
            report.blocked_requests.append(url)
            route.abort()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": 480, "height": 800})
            context.route("**/*", handle)
            page = context.new_page()
            page.on("pageerror", lambda e: report.page_errors.append(str(e)))

            def on_navigated(frame: Frame) -> None:
                # The first load of the artifact frame is its srcdoc. Anything else is the frame leaving the document.
                if frame != page.main_frame and frame.url not in ("about:srcdoc", "about:blank"):
                    report.navigations.append(frame.url)
                elif frame == page.main_frame and frame.url != harness_url:
                    report.navigations.append(frame.url)

            page.on("framenavigated", on_navigated)
            page.on("console", lambda m: report.console_errors.append(m.text) if m.type == "error" else None)
            page.goto(harness_url)

            try:
                page.wait_for_function("window.__synapse.ready === true", timeout=READY_TIMEOUT_MS)
                report.ready = True
            except Exception:
                report.ready = False

            if report.ready:
                try:
                    _exercise(page, report, interaction_seconds)
                except PlaywrightError as exc:
                    report.harness_error = str(exc).splitlines()[0]
            try:
                report.artifact_errors = list(page.evaluate("window.__synapse.errors"))
            except PlaywrightError as exc:
                report.harness_error = report.harness_error or str(exc).splitlines()[0]
        finally:
            browser.close()
    return report


def _frame(page) -> Frame:
    handle = page.query_selector("#artifact")
    frame = handle.content_frame() if handle else None
    if frame is None:
        raise RuntimeError("the artifact frame is missing")
    return frame


def _readout_texts(frame: Frame) -> list[str]:
    return frame.eval_on_selector_all("[data-synapse-readout]", "els => els.map(e => e.textContent)")


def _set_control(handle, which: str) -> None:  # noqa: ANN001
    """Move a control to exactly its 'min' or 'max' and fire the input event a user would."""
    handle.evaluate(
        """(el, which) => {
            el.value = which === 'max' ? el.max : el.min;
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        which,
    )


# Every element a user could operate must be a declared control; an undeclared one would never be exercised.
_INTERACTIVE = "input, select, textarea, button, [role=slider], [role=button], [contenteditable], a[href]"

_A11Y_JS = """() => {
  const problems = [];
  const text = (id) => { const n = id && document.getElementById(id); return n ? n.textContent.trim() : ''; };
  for (const el of document.querySelectorAll('[data-synapse-control]')) {
    const id = el.getAttribute('data-synapse-control');
    const lab = el.id && document.querySelector('label[for="' + el.id + '"]');
    const named = (lab && lab.textContent.trim()) || (el.getAttribute('aria-label') || '').trim() || text(el.getAttribute('aria-labelledby'));
    if (!named) problems.push("control '" + id + "' has no accessible name");
    if (el.type === 'range' && !(el.getAttribute('aria-valuetext') || '').trim()) problems.push("control '" + id + "' has no aria-valuetext");
  }
  for (const el of document.querySelectorAll('[data-synapse-readout]')) {
    const name = (el.getAttribute('aria-label') || '').trim() || text(el.getAttribute('aria-labelledby'));
    if (!name) problems.push("readout '" + el.getAttribute('data-synapse-readout') + "' has no accessible name");
  }
  return problems;
}"""


def _settle(page, ms: int = 150) -> None:
    page.wait_for_timeout(ms)


def _poke(page) -> None:
    """Real pointer and keyboard input: a handler on pointerdown, click or keydown must run during verification, not only the
    synthetic `input` events above (a navigation on pointerdown once passed because nothing ever pressed anything)."""
    box = page.query_selector("#artifact").bounding_box()  # type: ignore[union-attr]
    if box is None:
        return
    for fx in (0.15, 0.5, 0.85):
        for fy in (0.1, 0.35, 0.6, 0.85):
            page.mouse.click(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy)
    for key in ("Tab", "Tab", "ArrowRight", "ArrowLeft", "Enter", "Space"):
        page.keyboard.press(key)


def _exercise(page, report: RenderReport, interaction_seconds: float) -> None:
    frame = _frame(page)
    report.readouts = len(_readout_texts(frame))

    undeclared = frame.eval_on_selector_all(
        _INTERACTIVE,
        """els => els.filter(e => !e.hasAttribute('data-synapse-control')).map(e =>
            '<' + e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + '>')""",
    )
    report.undeclared_controls = list(undeclared)

    handles = frame.query_selector_all("[data-synapse-control]")
    seen: set[str] = set()
    for handle in handles:
        control_id = handle.get_attribute("data-synapse-control") or ""
        if control_id in seen:
            report.duplicate_controls.append(control_id)
        seen.add(control_id)

    for handle in handles:
        control_id = handle.get_attribute("data-synapse-control") or ""
        result = ControlResult(id=control_id)
        bounds = handle.bounding_box()
        result.height_px = bounds["height"] if bounds else 0.0

        # A readout that moves on its own would make every control look wired: require a quiet baseline first.
        _set_control(handle, "min")
        _settle(page)
        base = _readout_texts(frame)
        _settle(page, 300)
        if _readout_texts(frame) != base:
            result.stable = False

        _set_control(handle, "max")
        deadline = time.monotonic() + CONTROL_WIRE_TIMEOUT_MS / 1000
        while time.monotonic() < deadline:
            if _readout_texts(frame) != base:
                result.wired = True
                break
            page.wait_for_timeout(50)
        _settle(page)
        high = _readout_texts(frame)

        # Determinism: back to min must restore the baseline, and max again must restore the high reading.
        _set_control(handle, "min")
        _settle(page)
        if result.wired and _readout_texts(frame) != base:
            result.stable = False
        _set_control(handle, "max")
        _settle(page)
        if result.wired and _readout_texts(frame) != high:
            result.stable = False
        report.controls.append(result)

    report.a11y_problems = list(frame.evaluate(_A11Y_JS))

    # Scripted interaction: sweep every declared control and press real input for the time box.
    start = time.monotonic()
    while time.monotonic() - start < interaction_seconds:
        for handle in handles:
            for which in ("min", "max"):
                _set_control(handle, which)
                page.wait_for_timeout(100)
        _poke(page)
    report.interaction_seconds = time.monotonic() - start

    report.overflow_px = float(
        frame.evaluate("Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
    )
