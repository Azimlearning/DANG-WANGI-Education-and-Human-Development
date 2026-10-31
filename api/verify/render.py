# Ported from Azimlearning/GenUI-Education, Synapse-V3/evals/render_check.py (monorepo @ 835a2ce, v3 as of 2026-08) and
# docs/EVALS.md section 4. Read in full and adapted. Kept: the production-shaped harness (an iframe with sandbox="allow-scripts"
# and srcdoc inside a parent that listens for bridge messages) and the ready, control-wiring and no-errors assertions. Changed:
# wiring is judged by the declared readouts changing (not a screenshot diff, which a control's own label can satisfy), the
# network is closed except the Kit, the scripted interaction is time-boxed, and 360 px width and 44 px touch targets are checked.
"""The render harness (verification layer "render"): runs the Environment in headless Chromium the way the web app will.

It also drives every control through its declared grid, both extremes and every min/mid/max combination (L2), reads the Kit's audit at
each position, and hands the audits to api/verify/provenance.py: L1 (grounded, unaltered numbers) and L3 (each readout against an
independent reference). It asserts: `synapse_ready` within 5 s (a Free page has no Kit and cannot send it, so for `kit_lane=False` the harness itself
decides the page is ready once its document has loaded and painted twice); every declared control (`[data-synapse-control]`) changes at least one declared readout
(`[data-synapse-readout]`) within 1 s; no uncaught exception, console error or blocked request during a scripted interaction;
no horizontal overflow at 360 px; touch targets of at least 44 px. Anything else is a refusal that names the rule, and the control.

Sync Playwright is used on purpose: call this from a thread (`asyncio.to_thread`) when inside an event loop.
"""

from __future__ import annotations

import itertools
import json
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import ElementHandle, Frame, Route, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from api.verify import provenance as prov

READY_TIMEOUT_MS = 5_000
CONTROL_WIRE_TIMEOUT_MS = 1_000
INTERACTION_SECONDS = 10.0
MIN_TOUCH_TARGET_PX = 44
PHONE_WIDTH_PX = 360
MAX_GRID_POINTS = 500
MAX_PROBLEMS = 20

HARNESS = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">
<script>
  window.__synapse = { ready: false, errors: [], events: [], violations: [] };
  window.addEventListener("message", function (e) {
    var frame = document.getElementById("artifact");
    if (e.source !== frame.contentWindow) return;
    var d = e.data || {};
    if (d.type === "synapse_ready") window.__synapse.ready = true;
    if (d.type === "synapse_error") window.__synapse.errors.push(String(d.message));
    if (d.type === "synapse_event") window.__synapse.events.push(d);
    if (d.type === "synapse_violation") window.__synapse.violations.push((d.problems || []).join("; "));
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
    violations: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    blocked_requests: list[str] = field(default_factory=list)
    navigations: list[str] = field(default_factory=list)
    overflow_px: float = 0.0
    interaction_seconds: float = 0.0
    harness_error: str = ""
    audit0: dict | None = None
    problems_l1: list[prov.Problem] = field(default_factory=list)
    problems_l23: list[prov.Problem] = field(default_factory=list)
    grid_points: int = 0
    grid_truncated: bool = False
    reference_cases: int = 0
    models: list[tuple[str, tuple[tuple[str, float], ...]]] = field(default_factory=list)
    drag_problems: list[str] = field(default_factory=list)
    valve_problems: list[str] = field(default_factory=list)
    dial_problems: list[str] = field(default_factory=list)
    eye_problems: list[str] = field(default_factory=list)
    handle_problems: list[str] = field(default_factory=list)
    kit_lane: bool = True
    """False for a Free page: it has no Kit, so the harness decides readiness and the refusal message says so."""

    def refusal(self, require_controls: bool = True) -> tuple[str, str] | None:
        """The first failed rule as (rule, reason), or None when the Environment passed."""
        if not self.ready:
            if not self.kit_lane:
                return ("ready", f"the page did not finish loading its own document within {READY_TIMEOUT_MS} ms")
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
        if self.problems_l1:
            return (self.problems_l1[0].rule, self.problems_l1[0].reason)
        if require_controls and not self.controls:
            return ("no_controls", "no declared control found ([data-synapse-control])")
        for c in self.controls:
            if not c.wired:
                return (
                    "dead_control",
                    f"control '{c.id}' changed no declared readout within {CONTROL_WIRE_TIMEOUT_MS} ms",
                )
        if self.drag_problems:
            return ("drag_dead", self.drag_problems[0])
        if self.valve_problems:
            return ("valve_dead", self.valve_problems[0])
        if self.dial_problems:
            return ("dial_dead", self.dial_problems[0])
        if self.eye_problems:
            return ("eye_dead", self.eye_problems[0])
        if self.handle_problems:
            return ("handle_dead", self.handle_problems[0])
        for c in self.controls:
            if not c.stable:
                return (
                    "unstable_readout",
                    f"readouts changed without input or did not return to the same values around control '{c.id}'",
                )
        if self.problems_l23:
            return (self.problems_l23[0].rule, self.problems_l23[0].reason)
        if self.violations:
            return (
                "runtime_violation",
                "the Kit's own self-check tripped while the page ran: " + self.violations[0][:200],
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
    plan_models: list[dict] | None = None,
    kit_lane: bool = True,
    verify_mode: bool = True,
) -> RenderReport:
    """Run `html` in headless Chromium. `html` is the post-processed document (it carries our CSP)."""
    report = RenderReport(kit_lane=kit_lane)
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
            context = browser.new_context(viewport={"width": 480, "height": 800}, reduced_motion="reduce")
            context.route("**/*", handle)
            # Read once by the Kit at load: keep the page standing after a violation so every problem can be named.
            if verify_mode and kit_lane:
                # Only the Kit reads this flag. A Free page must not be able to tell it is being verified (D-41), so it never gets the flag.
                context.add_init_script("window.__SYNAPSE_VERIFY__ = true;")
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

            if kit_lane:
                try:
                    page.wait_for_function("window.__synapse.ready === true", timeout=READY_TIMEOUT_MS)
                    report.ready = True
                except Exception:
                    report.ready = False
            else:
                # A Free page has no Kit, and the L0 scan forbids `postMessage`, so it cannot send `synapse_ready`. The student's browser does not wait
                # for that message either. The harness itself decides: ready is the page's own document loaded and painted twice. The page cannot forge it.
                report.ready = _wait_until_loaded(page)

            if report.ready:
                try:
                    _exercise(page, report, interaction_seconds, plan_models, kit_lane)
                except PlaywrightError as exc:
                    report.harness_error = str(exc).splitlines()[0]
            try:
                report.artifact_errors = list(page.evaluate("window.__synapse.errors"))
                report.violations = list(page.evaluate("window.__synapse.violations"))
            except PlaywrightError as exc:
                report.harness_error = report.harness_error or str(exc).splitlines()[0]
        finally:
            browser.close()
    return report


def _wait_until_loaded(page) -> bool:  # noqa: ANN001
    """True when the artifact frame holds its own `srcdoc` document, finished loading, and has painted twice (the Kit's own ready timing). False on timeout,
    or when the frame left its srcdoc (a navigation), which `refusal()` then reports as not ready."""
    deadline = time.monotonic() + READY_TIMEOUT_MS / 1000
    while time.monotonic() < deadline:
        handle = page.query_selector("#artifact")
        frame = handle.content_frame() if handle else None
        if frame is not None and frame.url == "about:srcdoc":
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            try:
                frame.wait_for_load_state("load", timeout=remaining_ms)
                frame.evaluate("() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(() => done(true))))")
            except PlaywrightError:
                return False
            return frame.url == "about:srcdoc"
        page.wait_for_timeout(50)
    return False


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


# Every element a user could operate must be a declared control (or a Kit action button, which the audit proves the Kit made).
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
  // Hard constraint 10 for every OTHER thing a student can operate or must be able to read: named, 44 px, keyboard-focusable, a text equivalent for
  // every picture, no motion under prefers-reduced-motion, a document language.
  const shown = (el) => { const r = el.getBoundingClientRect(); const st = getComputedStyle(el); return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none'; };
  const nameOf = (el) => {
    const wrap = el.closest('label');
    const lab = el.id && document.querySelector('label[for="' + el.id + '"]');
    return ((lab && lab.textContent) || (wrap && wrap.textContent) || el.getAttribute('aria-label') || text(el.getAttribute('aria-labelledby')) || el.textContent || el.getAttribute('title') || '').trim();
  };
  for (const el of document.querySelectorAll('__INTERACTIVE__')) {
    if (el.hasAttribute('data-synapse-control') || !shown(el)) continue;
    const kind = el.tagName.toLowerCase() + (el.type ? '[' + el.type + ']' : '');
    const label = nameOf(el).slice(0, 30);
    if (!nameOf(el)) problems.push(kind + " has no accessible name");
    const box = (el.closest('label') || el).getBoundingClientRect();
    if (box.height < __MIN__ || box.width < __MIN__) problems.push(kind + " '" + label + "' is " + Math.round(box.width) + " by " + Math.round(box.height) + " px, under the __MIN__ px touch target");
    if (el.tabIndex < 0) problems.push(kind + " '" + label + "' cannot be reached with the keyboard");
  }
  for (const el of document.querySelectorAll('canvas, svg, img, video, audio, object, embed')) {
    if (!shown(el) || el.getAttribute('aria-hidden') === 'true') continue;
    const described = (el.getAttribute('aria-label') || '').trim() || text(el.getAttribute('aria-labelledby')) || (el.getAttribute('alt') || '').trim();
    if (!described) problems.push(el.tagName.toLowerCase() + " has no text equivalent (aria-label, aria-labelledby or alt)");
  }
  if (document.getAnimations().length > 0) problems.push("something animates even though the student asked for reduced motion");
  if (!(document.documentElement.lang || '').trim()) problems.push("the document has no lang attribute");
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


def _exercise(
    page, report: RenderReport, interaction_seconds: float, plan_models: list[dict] | None = None, kit_lane: bool = True
) -> None:
    frame = _frame(page)
    report.readouts = len(_readout_texts(frame))

    if kit_lane:
        # The state exactly as the page left it at load, before any input: the wiring checks below move every control, and the Kit
        # redraws its readouts as they move, which would erase a number a page forged at load.
        at_load = _audit(frame)
        _add(report.problems_l1, prov.l1_problems(at_load))
        if at_load is not None:
            _add(report.problems_l23, prov.l3_problems(at_load)[0])

    # A Kit action button (`data-synapse-action`) is exempt only in the Kit lane, where the audit proves the Kit made it. A Free page has no such proof, so
    # that marker there is just an unchecked button.
    exempt = " || e.hasAttribute('data-synapse-action')" if kit_lane else ""
    undeclared = frame.eval_on_selector_all(
        _INTERACTIVE,
        f"""els => els.filter(e => !(e.hasAttribute('data-synapse-control'){exempt})).map(e =>
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

    report.a11y_problems = list(
        frame.evaluate(_A11Y_JS.replace("__INTERACTIVE__", _INTERACTIVE).replace("__MIN__", str(MIN_TOUCH_TARGET_PX)))
    )

    if kit_lane:
        _audit_and_sweep(frame, handles, report, plan_models)
        _drive_drags(page, frame, report)
        _drive_valves(page, frame, report)
        _drive_dials(page, frame, report)
        _drive_eyes(page, frame, report)
        _drive_handles(page, frame, report)
    else:
        _drive_free_handles(page, frame, report)

    # Scripted interaction: sweep every declared control and press real input for the time box.
    start = time.monotonic()
    while time.monotonic() - start < interaction_seconds:
        for handle in handles:
            for which in ("min", "max"):
                _set_control(handle, which)
                page.wait_for_timeout(100)
        _poke(page)
    report.interaction_seconds = time.monotonic() - start
    if kit_lane:
        # A number inserted late (after the sweep, within the time box) is caught by one more audit at the end.
        final = _audit(frame)
        _add(report.problems_l1, prov.l1_problems(final))
        if final is not None:
            _add(report.problems_l23, prov.l3_problems(final)[0])

    report.overflow_px = float(
        frame.evaluate("Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
    )


def _mouse_drag(page, source, target) -> bool:  # noqa: ANN001
    """Press the mouse on the middle of `source`, move to the middle of `target` in steps, and release: a real drag, with the pointer events a user makes."""
    a, b = source.bounding_box(), target.bounding_box()
    if not a or not b:
        return False
    page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
    page.mouse.down()
    page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=8)
    page.mouse.up()
    return True


def _touch_drag(page, cdp, source, target) -> bool:  # noqa: ANN001
    """The same drag with a finger: touch events through the browser's input pipeline, so the page sees `pointerType: touch` and the browser's own touch-action rules apply."""
    a, b = source.bounding_box(), target.bounding_box()
    if not a or not b:
        return False
    x0, y0 = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
    x1, y1 = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for i in range(1, 9):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / 8, "y": y0 + (y1 - y0) * i / 8}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    return True


def _show_together(zone: ElementHandle, tray: ElementHandle) -> None:
    """Scroll so the drop place and the tray are both on screen (a bench part's tray is a row under the bench, not beside the place): the smallest element holding both is centred."""
    zone.evaluate(
        """(zone, tray) => {
            let box = zone;
            while (box && !box.contains(tray)) box = box.parentElement;
            (box || zone).scrollIntoView({ block: 'center', inline: 'nearest' });
        }""",
        tray,
    )


def _drive_drags(page, frame: Frame, report: RenderReport) -> None:  # noqa: ANN001
    """L2 for a control operated by dragging (`massHanger`). What must exist comes from the Kit's own audit (how many masses it made for which control), never from the page, so
    a page that renames, removes or hides the masses is caught by the count. Then EVERY mass is dragged onto the hanger with the mouse (each must raise the control by exactly one
    step and move the readouts), every mass is dragged off (each must lower it by one step), one mass is pressed from the keyboard, and one is dragged with a finger. A dead or blocked
    mass is refused as `drag_dead`. This is on top of the sweep, which sets the range input directly and would not notice."""
    audit = _audit(frame)
    if audit is None:
        return
    widgets = [w for w in audit.get("widgets", []) if w.get("kind") == "masses"]
    if not widgets and frame.query_selector("[data-synapse-drag]") is not None:
        report.drag_problems.append("the page has draggable masses the Kit did not report")
        return
    cdp = None
    for w in widgets:
        cid, want = str(w["id"]), int(w["masses"])
        try:
            control = frame.query_selector(f"[data-synapse-control='{cid}']")
            zone = frame.query_selector(f"[data-synapse-dropzone='{cid}']")
            tray = frame.query_selector(f"[data-synapse-tray='{cid}']")
            record = next((c for c in audit["controls"] if c["id"] == cid), None)
            if control is None or zone is None or tray is None or record is None:
                report.drag_problems.append(f"the masses for '{cid}' have no declared control, drop zone or tray")
                continue
            tokens = frame.query_selector_all(f"[data-synapse-drag='{cid}']")
            if len(tokens) != want:
                report.drag_problems.append(f"the Kit made {want} masses for '{cid}' but the page has {len(tokens)} it can drag")
                continue
            step = float(record["step"])
            tol = max(step * 0.02, 1e-9)

            def value(c=control) -> float:  # noqa: ANN001
                return float(c.input_value())

            def token(state: str, name=cid):  # noqa: ANN001, ANN202
                return frame.query_selector(f"[data-synapse-drag='{name}'][data-state='{state}']")

            _set_control(control, "min")
            _settle(page, 250)
            _show_together(zone, tray)
            # With the bench in view, audit once more: the layout half of the widget report (size, place, covered, faded) can only be read from a real layout, in view.
            _settle(page, 150)
            _add(report.problems_l1, prov.l1_problems(_audit(frame)))
            start = _readout_texts(frame)
            failed = False
            for n in range(want):  # every mass, one after another, onto the hanger
                mass, before = token("tray"), value()
                if mass is None or not _mouse_drag(page, mass, zone):
                    report.drag_problems.append(f"no mass could be dragged onto the hanger for '{cid}' (mass {n + 1} of {want})")
                    failed = True
                    break
                _settle(page, 250)
                if abs(value() - (before + step)) > tol:
                    report.drag_problems.append(f"dragging mass {n + 1} of {want} onto the hanger did not raise control '{cid}' by one step")
                    failed = True
                    break
                if n == 0 and _readout_texts(frame) == start:
                    report.drag_problems.append(f"dragging a mass onto the hanger changed no readout (control '{cid}')")
                    failed = True
                    break
            if failed:
                continue
            for n in range(want):  # and every mass off again
                mass, before = token("hung"), value()
                if mass is None or not _mouse_drag(page, mass, tray):
                    report.drag_problems.append(f"no mass could be dragged off the hanger for '{cid}' (mass {n + 1} of {want})")
                    failed = True
                    break
                _settle(page, 250)
                if abs(value() - (before - step)) > tol:
                    report.drag_problems.append(f"dragging mass {n + 1} of {want} off the hanger did not lower control '{cid}' by one step")
                    failed = True
                    break
            if failed:
                continue
            # The keyboard, for EVERY mass: focus it, press Enter (it hangs), press Enter again (it comes off). A page can swallow keys for all masses but one.
            for n in range(want):
                key = token("tray")
                if key is None:
                    report.drag_problems.append(f"no mass left to press from the keyboard for '{cid}' (mass {n + 1} of {want})")
                    failed = True
                    break
                key.focus()
                raised = value()
                page.keyboard.press("Enter")
                _settle(page, 200)
                if abs(value() - (raised + step)) > tol:
                    report.drag_problems.append(f"pressing mass {n + 1} of {want} with the keyboard did not raise control '{cid}' by one step")
                    failed = True
                    break
            if failed:
                continue
            for n in range(want):
                key = token("hung")
                if key is None:
                    break
                key.focus()
                raised = value()
                page.keyboard.press("Space")
                _settle(page, 200)
                if abs(value() - (raised - step)) > tol:
                    report.drag_problems.append(f"pressing hung mass {n + 1} of {want} with the keyboard (Space) did not take it off for '{cid}'")
                    failed = True
                    break
            if failed:
                continue
            # A finger, for EVERY mass, onto the hanger and off again.
            if cdp is None:
                cdp = page.context.new_cdp_session(page)
                cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
            for state, goal, sign, what in (("tray", zone, 1, "onto"), ("hung", tray, -1, "off")):
                for n in range(want):
                    mass, before = token(state), value()
                    if mass is None or not _touch_drag(page, cdp, mass, goal):
                        report.drag_problems.append(f"no mass could be dragged {what} the hanger with a finger for '{cid}' (mass {n + 1} of {want})")
                        failed = True
                        break
                    _settle(page, 250)
                    if abs(value() - (before + sign * step)) > tol:
                        report.drag_problems.append(f"dragging mass {n + 1} of {want} {what} the hanger with a finger did not move control '{cid}' by one step")
                        failed = True
                        break
                if failed:
                    break
            if failed:
                continue
            _set_control(control, "min")
            _settle(page, 200)
        except PlaywrightError as exc:
            # The harness lost the page or the input path; that is not evidence about the masses, so it is a harness error (fail closed), not drag_dead.
            report.harness_error = report.harness_error or f"driving the masses for '{cid}': {str(exc).splitlines()[0][:150]}"
    if cdp is not None:
        try:
            cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": False})
            cdp.detach()
        except PlaywrightError:
            pass


def _touch_hold(cdp, source, hold_ms: int, page) -> bool:  # noqa: ANN001
    """Put a finger on the middle of `source`, keep it there for `hold_ms`, lift it."""
    a = source.bounding_box()
    if not a:
        return False
    x, y = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    page.wait_for_timeout(hold_ms)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    return True


def _drive_valves(page, frame: Frame, report: RenderReport) -> None:  # noqa: ANN001
    """L2 for a control operated by a stopcock (`valve`). What must exist comes from the Kit's own audit. For each valve: a tap with the mouse lets out exactly one step, Enter and Space
    each let out one step, holding with the mouse runs at least two steps and stops when let go, and a finger does the same (a tap and a hold). A dead stopcock is `valve_dead`;
    a Playwright failure is a harness error."""
    audit = _audit(frame)
    if audit is None:
        return
    widgets = [w for w in audit.get("widgets", []) if w.get("kind") == "valve"]
    if not widgets:
        if frame.query_selector("[data-synapse-valve]") is not None:
            report.valve_problems.append("the page has a stopcock the Kit did not report")
        return
    cdp = None

    def one(w: dict) -> None:
        nonlocal cdp
        cid = str(w["id"])
        try:
            control = frame.query_selector(f"[data-synapse-control='{cid}']")
            buttons = frame.query_selector_all(f"[data-synapse-valve='{cid}']")
            record = next((c for c in audit["controls"] if c["id"] == cid), None)
            if control is None or record is None or len(buttons) != 1:
                report.valve_problems.append(f"the stopcock for '{cid}' is missing, or the page has more than the one the Kit made")
                return
            button = buttons[0]
            step = float(record["step"])
            tol = max(step * 0.02, 1e-9)

            def value(c=control) -> float:  # noqa: ANN001
                return float(c.input_value())

            def fresh() -> None:
                _set_control(control, "min")
                _settle(page, 250)

            def once(label: str, act) -> bool:  # noqa: ANN001
                fresh()
                before = value()
                act()
                _settle(page, 250)
                if abs(value() - (before + step)) > tol:
                    report.valve_problems.append(f"{label} did not let out exactly one step for '{cid}'")
                    return False
                return True

            def holds(label: str, act) -> bool:  # noqa: ANN001
                before = value()
                act()
                after = value()
                if after - before < 2 * step - tol:
                    report.valve_problems.append(f"{label} did not run at least two steps for '{cid}'")
                    return False
                steps = (after - before) / step
                if abs(steps - round(steps)) > 0.02:
                    report.valve_problems.append(f"{label} left '{cid}' between two steps")
                    return False
                page.wait_for_timeout(450)
                if abs(value() - after) > tol:
                    report.valve_problems.append(f"the liquid kept running after {label} ended, for '{cid}'")
                    return False
                return True

            button.scroll_into_view_if_needed()
            _settle(page, 150)
            _add(report.problems_l1, prov.l1_problems(_audit(frame)))
            box = button.bounding_box()
            if not box:
                report.valve_problems.append(f"the stopcock for '{cid}' has no place on the page")
                return
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

            def mouse_tap() -> None:
                page.mouse.move(cx, cy)
                page.mouse.down()
                page.mouse.up()

            def mouse_hold() -> None:
                page.mouse.move(cx, cy)
                page.mouse.down()
                page.wait_for_timeout(850)
                page.mouse.up()

            fresh()
            start = _readout_texts(frame)  # at the lowest position, before anything is let out
            if not once("a tap on the stopcock", mouse_tap):
                return
            if _readout_texts(frame) == start:
                report.valve_problems.append(f"letting out liquid changed no readout (control '{cid}')")
                return
            if not once("pressing Enter on the stopcock", lambda: (button.focus(), page.keyboard.press("Enter"))):
                return
            if not once("pressing Space on the stopcock", lambda: (button.focus(), page.keyboard.press("Space"))):
                return
            fresh()
            if not holds("holding the stopcock with the mouse", mouse_hold):
                return
            if cdp is None:
                cdp = page.context.new_cdp_session(page)
                cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
            fresh()
            if not once("a finger tap on the stopcock", lambda: _touch_hold(cdp, button, 40, page)):
                return
            fresh()
            if not holds("holding the stopcock with a finger", lambda: _touch_hold(cdp, button, 850, page)):
                return
            _set_control(control, "min")
            _settle(page, 200)
        except PlaywrightError as exc:
            report.harness_error = report.harness_error or f"driving the stopcock for '{cid}': {str(exc).splitlines()[0][:150]}"
    for w in widgets:
        one(w)
    if cdp is not None:
        try:
            cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": False})
            cdp.detach()
        except PlaywrightError:
            pass


def _drive_dials(page, frame: Frame, report: RenderReport) -> None:  # noqa: ANN001
    """L2 for a control turned like a knob (`dial`). What must exist comes from the Kit's own audit. For each dial: the mouse turns the knob to the middle, the top and the bottom of its range
    (the control must land on the matching step each time), a finger turns it to the middle, and the arrow keys on its range input move it one step each way. A dial that does not follow
    is `dial_dead`; extra knobs the Kit did not report are refused; a Playwright failure is a harness error."""
    audit = _audit(frame)
    if audit is None:
        return
    widgets = [w for w in audit.get("widgets", []) if w.get("kind") == "dial"]
    if not widgets:
        if frame.query_selector("[data-synapse-dial]") is not None:
            report.dial_problems.append("the page has a dial the Kit did not report")
        return
    cdp = None

    def one(w: dict) -> None:
        nonlocal cdp
        cid = str(w["id"])
        try:
            control = frame.query_selector(f"[data-synapse-control='{cid}']")
            knobs = frame.query_selector_all(f"[data-synapse-dial='{cid}']")
            record = next((c for c in audit["controls"] if c["id"] == cid), None)
            if control is None or record is None or len(knobs) != 1:
                report.dial_problems.append(f"the dial for '{cid}' is missing, or the page has more than the one the Kit made")
                return
            knob: ElementHandle = knobs[0]
            lo, step, grid = float(record["min"]), float(record["step"]), int(record["grid"])
            tol = max(step * 0.02, 1e-12)

            def value(c=control) -> float:  # noqa: ANN001
                return float(c.input_value())

            knob.scroll_into_view_if_needed()
            _settle(page, 150)
            _add(report.problems_l1, prov.l1_problems(_audit(frame)))
            box = knob.bounding_box()
            if not box or box["width"] < 44 or box["height"] < 44:
                report.dial_problems.append(f"the dial for '{cid}' has no room for a finger")
                return
            cx, cy, r = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, box["width"] / 2

            def locate() -> None:
                """Measure the knob again: a sentence above it that the dial changes (the fermentation scene's, on a narrow page) moves the knob between two turns."""
                nonlocal cx, cy, r
                knob.scroll_into_view_if_needed()
                now = knob.bounding_box()
                if now:
                    cx, cy, r = now["x"] + now["width"] / 2, now["y"] + now["height"] / 2, now["width"] / 2

            def point(index: int) -> tuple[float, float]:
                angle = math.radians(-135 + 270 * index / grid)
                return cx + 0.8 * r * math.sin(angle), cy - 0.8 * r * math.cos(angle)

            def turn(index: int, touch: bool = False) -> None:
                nonlocal cdp
                locate()
                x1, y1 = point(index)
                x0, y0 = point(0)  # start at the first mark, so the press alone cannot satisfy a target anywhere else
                if touch:
                    if cdp is None:
                        cdp = page.context.new_cdp_session(page)
                        cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
                    for i in range(1, 9):
                        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / 8, "y": y0 + (y1 - y0) * i / 8}]})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                else:
                    page.mouse.move(x0, y0)
                    page.mouse.down()
                    page.mouse.move(x1, y1, steps=8)
                    page.mouse.up()
                _settle(page, 200)

            _set_control(control, "min")
            _settle(page, 200)
            start = _readout_texts(frame)
            for label, touch, indexes in (("with the mouse", False, (grid // 2, grid, 0)), ("with a finger", True, (grid // 2, grid, 0))):
                for index in indexes:
                    turn(index, touch)
                    want = lo + index * step
                    if abs(value() - want) > tol:
                        report.dial_problems.append(f"turning the dial for '{cid}' {label} to step {index} of {grid} left the control at {value():g}, not {want:g}")
                        return
                    if index == grid // 2 and not touch and _readout_texts(frame) == start:
                        report.dial_problems.append(f"turning the dial changed no readout (control '{cid}')")
                        return
            # the keyboard: the dial's range input is its accessible control, so a real arrow key must move it one step each way
            _set_control(control, "min")
            _settle(page, 150)
            control.focus()
            page.keyboard.press("ArrowRight")
            _settle(page, 150)
            kit_value = next((c["value"] for c in (_audit(frame) or {}).get("controls", []) if c["id"] == cid), None)  # the Kit's own value, not only the input's
            if abs(value() - (lo + step)) > tol or kit_value is None or abs(float(kit_value) - (lo + step)) > tol:
                report.dial_problems.append(f"pressing the right arrow on the range input of the dial for '{cid}' did not move it one step")
                return
            page.keyboard.press("ArrowLeft")
            _settle(page, 150)
            kit_value = next((c["value"] for c in (_audit(frame) or {}).get("controls", []) if c["id"] == cid), None)
            if abs(value() - lo) > tol or kit_value is None or abs(float(kit_value) - lo) > tol:
                report.dial_problems.append(f"pressing the left arrow on the range input of the dial for '{cid}' did not move it back one step")
                return
            # with the knob turned, the picture must still be what the numbers say
            turn(grid // 2)
            _add(report.problems_l1, prov.l1_problems(_audit(frame)))
            _set_control(control, "min")
            _settle(page, 200)
        except PlaywrightError as exc:
            report.harness_error = report.harness_error or f"driving the dial for '{cid}': {str(exc).splitlines()[0][:150]}"

    for w in widgets:
        one(w)
    if cdp is not None:
        try:
            cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": False})
            cdp.detach()
        except PlaywrightError:
            pass


EYE_WORDS = {"en": ("above", "level", "below"), "ms": ("di atas", "adil", "di bawah")}
"""The words the eye's sentence must contain when the eye is above, level with and below the meniscus, by the page's language (D-62). The sentence is the Kit's own and the Kit's table
is where these words come from (`eyeAbove`, `eyeLevel`, `eyeBelow`)."""


def _drive_handles(page, frame: Frame, report: RenderReport) -> None:  # noqa: ANN001
    """L2 for a grip on a bench part (W17, D-69). What must exist comes from the Kit's own audit: one grip per channel bound to a slider that the catalogue lets the student grab.
    For each grip the mouse drags it to the far end of its line (or the top of its arc), to the near end and to the middle, and a finger drags it to the far end and back. The
    slider must land where the Kit's mapping puts it (exactly at the ends, within a step in the middle) and the readouts must move. A grip that does not follow, or a page with grips
    the Kit did not make, is `handle_dead`; a Playwright failure is a harness error."""
    audit = _audit(frame)
    if audit is None:
        return
    widgets = [w for w in audit.get("widgets", []) if w.get("kind") == "handle"]
    grips = frame.query_selector_all("[data-synapse-handle]")
    if len(grips) != len(widgets):
        report.handle_problems.append(f"the page has {len(grips)} handles on its apparatus and the Kit made {len(widgets)}")
        return
    cdp = None

    def defaults() -> None:
        """Every control at the value the student first sees. The sweeps before this leave controls at their ends, and a graph of current against resistance has
        no readout to move while the voltage sits at 0."""
        for c in audit.get("controls", []):
            el = frame.query_selector(f"[data-synapse-control='{c['id']}']")
            if el is not None:
                _set_value(el, float(c["default"]))
        _settle(page, 150)

    def one(w: dict) -> None:
        nonlocal cdp
        hid, cid = str(w.get("id")), str(w.get("control"))
        defaults()
        try:
            grip = frame.query_selector(f"[data-synapse-handle='{hid}']")
            control = frame.query_selector(f"[data-synapse-control='{cid}']")
            record = next((c for c in audit["controls"] if c["id"] == cid), None)
            grab = w.get("grab") or {}
            if grip is None or control is None or record is None or not grab:
                report.handle_problems.append(f"the handle {hid} has no grip, no declared control or no line to run along")
                return
            svg = grip.evaluate_handle("el => el.ownerSVGElement").as_element()
            if svg is None:
                report.handle_problems.append(f"the handle {hid} is not on a drawing")
                return
            lo, hi, step = float(record["min"]), float(record["max"]), float(record["step"])
            angle = "pivot" in grab
            full = float(w.get("full") or 0) if not angle else 0.0
            # W18: a handle on a graph or on the planets brings its own drawing box and the control value at the start of its line; an apparatus grip has neither
            # (the 120 by 140 part, and a drawn fraction that starts at nothing).
            box_w, box_h = (float(v) for v in (w.get("box") or (120, 140)))
            origin = float(w.get("origin") or 0.0)
            if not angle and full <= 0:
                report.handle_problems.append(f"the handle {hid} has no drawing scale")
                return
            tol = max(step * 0.02, 1e-9)

            def value() -> float:
                return float(control.input_value())

            def expect(drawn: float) -> float:
                raw = drawn if angle else origin + drawn * (full - origin)
                c = min(hi, max(lo, raw))
                return min(hi, lo + round((c - lo) / step) * step)

            def target(drawn: float) -> tuple[float, float] | None:
                box = svg.bounding_box()
                if not box:
                    return None
                k = min(box["width"] / box_w, box["height"] / box_h)
                ox, oy = box["x"] + (box["width"] - box_w * k) / 2, box["y"] + (box["height"] - box_h * k) / 2
                if angle:
                    a = math.radians(min(60.0, max(0.0, drawn)))
                    x, y = grab["pivot"][0] + grab["radius"] * math.cos(a), grab["pivot"][1] - grab["radius"] * math.sin(a)
                else:
                    t = min(1.0, max(0.0, drawn))
                    x = grab["from"][0] + t * (grab["to"][0] - grab["from"][0])
                    y = grab["from"][1] + t * (grab["to"][1] - grab["from"][1])
                return ox + x * k, oy + y * k

            def drag(drawn: float, touch: bool) -> bool:
                nonlocal cdp
                grip.scroll_into_view_if_needed()
                box, end = grip.bounding_box(), target(drawn)
                if not box or end is None:
                    return False
                x0, y0 = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                x1, y1 = end
                if touch:
                    if cdp is None:
                        cdp = page.context.new_cdp_session(page)
                        cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
                    for i in range(1, 9):
                        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / 8, "y": y0 + (y1 - y0) * i / 8}]})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                else:
                    page.mouse.move(x0, y0)
                    page.mouse.down()
                    page.mouse.move(x1, y1, steps=8)
                    page.mouse.up()
                _settle(page, 200)
                return True

            grip.scroll_into_view_if_needed()
            _settle(page, 150)
            _add(report.problems_l1, prov.l1_problems(_audit(frame)))
            _set_control(control, "min")
            _settle(page, 200)
            start = _readout_texts(frame)
            far, near, middle = (60.0, 0.0, 30.0) if angle else (1.0, 0.0, 0.5)
            for how, touch, stops in (("with the mouse", False, (far, near, middle)), ("with a finger", True, (far, near))):
                for drawn in stops:
                    if not drag(drawn, touch):
                        report.handle_problems.append(f"the handle {hid} could not be dragged {how}")
                        return
                    want = expect(drawn)
                    if abs(value() - want) > (step * 1.01 if drawn == middle else tol):
                        report.handle_problems.append(f"dragging the handle {hid} {how} left '{cid}' at {value():g}, not {want:g}")
                        return
                    if drawn == far and not touch and want != lo and _readout_texts(frame) == start:
                        report.handle_problems.append(f"dragging the handle {hid} changed no readout")
                        return
            # with the grip moved, the picture must still be what the numbers say
            drag(middle, False)
            _add(report.problems_l1, prov.l1_problems(_audit(frame)))
            _set_control(control, "min")
            _settle(page, 200)
        except PlaywrightError as exc:
            report.harness_error = report.harness_error or f"driving the handle {hid}: {str(exc).splitlines()[0][:150]}"

    for w in widgets:
        one(w)
    if cdp is not None:
        try:
            cdp.detach()
        except PlaywrightError:
            pass


FREE_HANDLE_LIMIT = 8


def _drive_free_handles(page, frame: Frame, report: RenderReport) -> None:  # noqa: ANN001
    """L2 for a model-written page's handles (W17, D-71). An element marked `data-synapse-handle="<slider id>"` is a pointer surface for that slider: the mouse drags it right, left,
    down and up from its centre, and the slider must move at least once. A handle that also names a drop target (`data-synapse-target="<element id>"`, W20) is dragged onto
    that element instead, and the drop must move the slider. A handle that names no slider, or moves nothing, is `handle_dead`. The slider stays the only control and
    the source of every number, so the sweep's checks are unchanged."""
    grips = frame.query_selector_all("[data-synapse-handle]")
    if len(grips) > FREE_HANDLE_LIMIT:
        report.handle_problems.append(f"the page has {len(grips)} handles; at most {FREE_HANDLE_LIMIT}")
        return
    view = page.viewport_size or {"width": 1280, "height": 900}
    for grip in grips:
        try:
            cid = grip.get_attribute("data-synapse-handle") or ""
            control = frame.query_selector(f"[data-synapse-control='{cid}']") if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", cid) else None
            if control is None:
                report.handle_problems.append(f"a handle names '{cid[:40]}', which is not a slider on the page")
                return
            _set_control(control, "min")
            _settle(page, 150)
            before, moved = control.input_value(), False
            # W20 (D-80): a handle that is dropped onto something (a mass onto a pan, a test mass onto a planet) names it, and is dragged there and nowhere else.
            aim = grip.get_attribute("data-synapse-target")
            if aim is not None:
                spot = frame.query_selector(f"#{aim}") if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", aim) else None
                grip.scroll_into_view_if_needed()
                box, goal = grip.bounding_box(), spot.bounding_box() if spot is not None else None
                if box is None or goal is None:
                    report.handle_problems.append(f"the handle for '{cid}' names the drop target '{aim[:40]}', which is not on the page")
                    return
                page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                page.mouse.down()
                page.mouse.move(goal["x"] + goal["width"] / 2, goal["y"] + goal["height"] / 2, steps=10)
                page.mouse.up()
                _settle(page, 250)
                if control.input_value() == before:
                    report.handle_problems.append(f"dropping the handle for '{cid}' onto '{aim}' did not move it")
                    return
                _set_control(control, "min")
                _settle(page, 150)
                continue
            for dx, dy in ((90, 0), (-180, 0), (90, 90), (0, -180)):
                grip.scroll_into_view_if_needed()
                box = grip.bounding_box()
                if not box:
                    break
                x0, y0 = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                x1, y1 = min(view["width"] - 2, max(2, x0 + dx)), min(view["height"] - 2, max(2, y0 + dy))
                page.mouse.move(x0, y0)
                page.mouse.down()
                page.mouse.move(x1, y1, steps=8)
                page.mouse.up()
                _settle(page, 200)
                if control.input_value() != before:
                    moved = True
                    break
            if not moved:
                report.handle_problems.append(f"dragging the handle for '{cid}' did not move it")
                return
            _set_control(control, "min")
            _settle(page, 150)
        except PlaywrightError as exc:
            report.harness_error = report.harness_error or f"driving a handle: {str(exc).splitlines()[0][:150]}"
            return


def _drive_eyes(page, frame: Frame, report: RenderReport) -> None:  # noqa: ANN001
    """L2 for the eye of a titration scene. What must exist comes from the Kit's audit. With the control high, the eye is sent to the top and bottom of the burette by the keyboard
    (the sentence must say above, then below), dragged to the meniscus with the mouse and with a finger (level), and dragged to the top and bottom (above, below). A dead eye is
    `eye_dead`. The sentence is Kit-owned text, so reading it is reading the Kit."""
    audit = _audit(frame)
    if audit is None:
        return
    scenes = [w for w in audit.get("widgets", []) if w.get("kind") == "scene" and w.get("eye")]
    if not scenes:
        if frame.query_selector("[data-synapse-eye]") is not None:
            report.eye_problems.append("the page has an eye the Kit did not report")
        return
    cdp = None

    def one(w: dict) -> None:
        nonlocal cdp
        try:
            source = w.get("sourceChain") or {}
            record = next((c for c in audit["controls"] if c["id"] == source.get("id")), None)
            control = frame.query_selector(f"[data-synapse-control='{source.get('id')}']")
            eyes = frame.query_selector_all("[data-synapse-eye]")
            if control is None or record is None or len(eyes) != 1:
                report.eye_problems.append("the burette scene is missing its eye or its control, or the page has more than the one eye the Kit made")
                return
            eye: ElementHandle = eyes[0]
            # Everything else is found from the Kit's own eye (its widget wrapper), not by a marker anywhere on the page that a decoy could carry.
            wrapper = eye.evaluate_handle("e => e.closest('.syn-titr')").as_element()
            note = wrapper.query_selector("[data-synapse-eye-status]") if wrapper else None
            marker = wrapper.query_selector("[data-synapse-meniscus]") if wrapper else None
            root = wrapper.query_selector("svg.syn-titration") if wrapper else None
            if note is None or marker is None or root is None:
                report.eye_problems.append("the burette scene is missing its sentence, its meniscus or its picture")
                return
            note_h: ElementHandle = note
            lang = str(frame.evaluate("document.documentElement.lang || 'en'"))[:2].lower()
            above, level, below = EYE_WORDS.get(lang, EYE_WORDS["en"])
            marker_h: ElementHandle = marker
            root_h: ElementHandle = root
            # With the burette about half run in, the meniscus is clear of both ends, so the eye can be above, level and below it.
            full = float(w.get("full") or 0)
            step = float(record["step"])
            target = min(float(record["max"]), max(float(record["min"]), float(record["min"]) + round((full / 2 - float(record["min"])) / step) * step))
            if not (0.08 < target / full < 0.92):
                return  # a range this close to an end of the burette cannot be driven both ways; the Plan checks allow it, and nothing is claimed about it
            _set_value(control, target)
            _settle(page, 250)
            eye.scroll_into_view_if_needed()
            _settle(page, 150)
            if not (note_h.is_visible() and root_h.is_visible()):
                report.eye_problems.append("the eye's sentence or the burette picture is not visible")
                return
            def words() -> str:
                return (note_h.inner_text() or "").strip()

            eye.focus()
            page.keyboard.press("Home")
            _settle(page, 120)
            if above not in words():
                report.eye_problems.append(f"moving the eye to the top of the burette from the keyboard did not say it was above the meniscus ({words()[:60]!r})")
                return
            page.keyboard.press("End")
            _settle(page, 120)
            if below not in words():
                report.eye_problems.append(f"moving the eye to the bottom of the burette from the keyboard did not say it was below the meniscus ({words()[:60]!r})")
                return

            def drag_eye_to(y_target: float, touch: bool = False) -> bool:
                nonlocal cdp
                e = eye.bounding_box()
                if not e:
                    return False
                x, y = e["x"] + e["width"] / 2, e["y"] + e["height"] / 2
                if touch:
                    if cdp is None:
                        cdp = page.context.new_cdp_session(page)
                        cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
                    for i in range(1, 9):
                        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y + (y_target - y) * i / 8}]})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                else:
                    page.mouse.move(x, y)
                    page.mouse.down()
                    page.mouse.move(x, y_target, steps=8)
                    page.mouse.up()
                _settle(page, 150)
                return True

            def meniscus_y() -> float:
                m = marker_h.bounding_box()
                return (m["y"] + m["height"] / 2) if m else float("nan")

            box = root_h.bounding_box()
            if not box:
                report.eye_problems.append("the burette picture has no place on the page")
                return
            scale = min(box["width"] / 220, box["height"] / 280)
            top_of = box["y"] + (box["height"] - 280 * scale) / 2

            def burette_at(fraction: float) -> float:
                return top_of + (20 + fraction * 130) * scale

            for label, touch in (("with the mouse", False), ("with a finger", True)):
                if not drag_eye_to(burette_at(0.02), touch) or above not in words():
                    report.eye_problems.append(f"dragging the eye to the top of the burette {label} did not say it was above the meniscus ({words()[:60]!r})")
                    break
                if not drag_eye_to(meniscus_y(), touch) or level not in words():
                    report.eye_problems.append(f"dragging the eye to the meniscus {label} did not say it was level ({words()[:60]!r})")
                    break
                if not drag_eye_to(burette_at(0.98), touch) or below not in words():
                    report.eye_problems.append(f"dragging the eye to the bottom of the burette {label} did not say it was below the meniscus ({words()[:60]!r})")
                    break
            # with the eye moved, the picture must still be what the numbers say (structure and layout)
            _add(report.problems_l1, prov.l1_problems(_audit(frame)))
            _set_control(control, "min")
            _settle(page, 200)
        except PlaywrightError as exc:
            report.harness_error = report.harness_error or f"driving the eye: {str(exc).splitlines()[0][:150]}"
    for w in scenes:
        one(w)
    if cdp is not None:
        try:
            cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": False})
            cdp.detach()
        except PlaywrightError:
            pass


# ── L1, L2, L3: the Kit's audit at every grid and extreme position ──────────────────────────────────────────────────────

_AUDIT_JS = "() => (window.Synapse && typeof window.Synapse.audit === 'function') ? window.Synapse.audit() : null"


def _audit(frame: Frame) -> dict | None:
    try:
        return frame.evaluate(_AUDIT_JS)
    except PlaywrightError as exc:
        message = str(exc).lower()
        if "navigat" in message or "context was destroyed" in message or "target closed" in message:
            raise
        return None  # the audit function itself threw: L1 reports kit_missing


def _set_vs_reported(pt: dict[str, float], snapshot: dict | None) -> list[prov.Problem]:
    """The control values the harness set must be the ones the Kit reports (a page that bends what a control means is refused)."""
    if not isinstance(snapshot, dict):
        return []
    reported = {c["id"]: c for c in snapshot.get("controls", [])}
    out = []
    for control_id, want in pt.items():
        c = reported.get(control_id)
        if c is None:
            continue
        tolerance = float(c.get("step", 0.0)) / 2 + 1e-9
        if abs(float(c["value"]) - want) > tolerance:
            out.append(
                prov.Problem(
                    "control_mismatch",
                    f"the harness set control '{control_id}' to {want} but the Kit reports {c['value']}",
                )
            )
    return out


def _set_value(handle, value: float) -> None:  # noqa: ANN001
    handle.evaluate(
        "(el, v) => { el.value = String(v); el.dispatchEvent(new Event('input', { bubbles: true })); }",
        value,
    )


def _positions(c: dict) -> list[float]:
    return [c["min"] + (c["max"] - c["min"]) * i / c["grid"] for i in range(int(c["grid"]) + 1)]


def _points(controls: list[dict]) -> tuple[list[dict[str, float]], bool]:
    """Default point; each control across its grid with the others at default; every min, mid, max combination. Capped."""
    defaults = {c["id"]: float(c["default"]) for c in controls}
    ids = [c["id"] for c in controls]
    points: list[dict[str, float]] = [dict(defaults)]
    for c in controls:
        points += [{**defaults, c["id"]: float(v)} for v in _positions(c)]
    levels = [[c["min"], (c["min"] + c["max"]) / 2, c["max"]] for c in controls]
    points += [dict(zip(ids, map(float, combo), strict=True)) for combo in itertools.product(*levels)]
    seen: set[tuple] = set()
    unique: list[dict[str, float]] = []
    for pt in points:
        key = tuple(sorted(pt.items()))
        if key not in seen:
            seen.add(key)
            unique.append(pt)
    return unique[:MAX_GRID_POINTS], len(unique) > MAX_GRID_POINTS


def _add(found: list[prov.Problem], new: list[prov.Problem]) -> None:
    for problem in new:
        if problem not in found and len(found) < MAX_PROBLEMS:
            found.append(problem)


def _audit_and_sweep(frame: Frame, handles: list, report: RenderReport, plan_models: list[dict] | None) -> None:
    first = _audit(frame)
    report.audit0 = first
    _add(report.problems_l1, prov.l1_problems(first))
    if first is None:
        return
    _add(report.problems_l1, prov.plan_problems(first, plan_models))
    for _, chain in prov.all_chains(first):
        for m in prov.models_in(chain):
            if m not in report.models:
                report.models.append(m)

    by_id = {h.get_attribute("data-synapse-control"): h for h in handles}
    controls = [c for c in first.get("controls", []) if c["id"] in by_id]
    points, report.grid_truncated = _points(controls)
    for pt in points:
        for control_id, value in pt.items():
            _set_value(by_id[control_id], value)
        snapshot = _audit(frame)
        report.grid_points += 1
        _add(report.problems_l1, _set_vs_reported(pt, snapshot))
        _add(report.problems_l1, prov.l1_problems(snapshot))
        if snapshot is not None:
            l3, compared = prov.l3_problems(snapshot)
            report.reference_cases += compared
            _add(report.problems_l23, l3)
        if len(report.problems_l1) >= MAX_PROBLEMS:
            break
    defaults = {c["id"]: float(c["default"]) for c in controls}
    for control_id, value in defaults.items():
        _set_value(by_id[control_id], value)
