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
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Route, sync_playwright

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
