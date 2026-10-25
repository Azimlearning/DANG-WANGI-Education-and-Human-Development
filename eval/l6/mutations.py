"""L6: planted defects. Each mutation takes a good page (or the built Kit) and breaks it in one named way.

The point is a measured detection rate, not a clean sheet. A mutation says what it expects: `refuse` (a defect the verifier should stop)
or `accept` (a neutral change that must NOT be refused, which measures false positives). Mutations marked `known_miss` are defects we
believe the verifier cannot see today; they are kept in the set so the miss is on the record and a future layer that closes one flips
the pinned expectation. The classes here are the ones someone thought of. They are not the space of bugs.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

READY = "Synapse.bridge.ready();"
SPRING = "reference-spring.html"
OHM = "reference-ohm.html"
PRESSURE = "reference-pressure.html"
OHM_GRAPH = "reference-ohm-graph.html"
MASSES = "reference-masses.html"
TITR = "reference-titration.html"


def patch_fn(names: list[str], body: str) -> tuple[str, str]:
    """A (regex, replacement) that rewrites a built science model's `fn` body. The bundle is minified, so the destructured argument
    names change from build to build; the pattern captures them and `body` refers to the arguments as {name}."""
    pattern = r"fn:\(\{" + ",".join(f"{n}:(\\w+)" for n in names) + r"\}\)=>[^,]+?(?=,citation:)"
    args = ",".join(f"{n}:\\{i + 1}" for i, n in enumerate(names))
    filled = body
    for i, n in enumerate(names):
        filled = filled.replace("{" + n + "}", f"\\{i + 1}")
    return pattern, "fn:({" + args + "})=>" + filled


@dataclass(frozen=True)
class Mutation:
    id: str
    klass: str  # physics | provenance | trust | structure | neutral
    what: str
    base: str
    expect: str  # "refuse", "accept", or "neutralise" (accepted only after our CSP is the one and only policy, first in the head)
    edit: Callable[[str], str] = lambda html: html
    kit_edit: tuple[str, str] | None = None  # (old, new) applied to the copied Kit bundle
    known_miss: bool = False
    note: str = ""
    layers_expected: tuple[str, ...] = field(default=())


def sub(old: str, new: str) -> Callable[[str], str]:
    def apply(html: str) -> str:
        if old not in html:
            raise AssertionError(f"mutation anchor not found: {old!r}")
        return html.replace(old, new, 1)

    return apply


def before_ready(js: str) -> Callable[[str], str]:
    return sub(READY, js + "\n  " + READY)


MUTATIONS: list[Mutation] = [
    # ── physics bugs planted in the Kit bundle (the verifier's references must catch them) ──────────────────────────────────
    Mutation(
        "kit-hookes-multiplies",
        "physics",
        "Hooke's model multiplies load by k instead of dividing",
        SPRING,
        "refuse",
        kit_edit=patch_fn(["load", "k"], "{load}*{k}"),
    ),
    Mutation(
        "kit-hookes-offset",
        "physics",
        "Hooke's model adds a 1 mm offset",
        SPRING,
        "refuse",
        kit_edit=patch_fn(["load", "k"], "{load}/{k}+0.001"),
    ),
    Mutation(
        "kit-hookes-high-load",
        "physics",
        "Hooke's model saturates above 8 N",
        SPRING,
        "refuse",
        kit_edit=patch_fn(["load", "k"], "Math.min({load},8)/{k}"),
    ),
    Mutation(
        "kit-ohm-power",
        "physics",
        "Ohm's model returns V times R",
        OHM,
        "refuse",
        kit_edit=patch_fn(["voltage", "resistance"], "{voltage}*{resistance}"),
    ),
    Mutation(
        "kit-ohm-swapped",
        "physics",
        "Ohm's model divides resistance by voltage",
        OHM,
        "refuse",
        kit_edit=patch_fn(["voltage", "resistance"], "{resistance}/Math.max({voltage},1e-9)"),
    ),
    Mutation(
        "kit-pressure-halved",
        "physics",
        "pressure model drops a factor of two",
        PRESSURE,
        "refuse",
        kit_edit=patch_fn(["depth", "density", "g"], "{depth}*{density}*{g}/2"),
    ),
    Mutation(
        "kit-pressure-ignores-g",
        "physics",
        "pressure model uses 9.81 whatever g the page sets",
        PRESSURE,
        "refuse",
        kit_edit=patch_fn(["depth", "density", "g"], "{depth}*{density}*9.81"),
    ),
    Mutation(
        "kit-convert-wrong-factor",
        "physics",
        "the Kit converts Pa to kPa by 100",
        PRESSURE,
        "refuse",
        kit_edit=(re.escape('kPa:{dim:"pressure",toSI:1e3}'), 'kPa:{dim:"pressure",toSI:100}'),
    ),
    Mutation(
        "kit-hookes-narrow-spike",
        "physics",
        "Hooke's model is wrong only at exactly 3.14159 N (between grid points)",
        SPRING,
        "refuse",
        kit_edit=patch_fn(["load", "k"], "Math.abs({load}-3.14159)<1e-9?0:{load}/{k}"),
        known_miss=True,
        note="Verification samples defaults, grids and extremes; a bug confined to an unsampled point passes.",
    ),
    # ── provenance defects in the page ──────────────────────────────────────────────────────────────────────────────────────
    Mutation(
        "page-wrong-k",
        "provenance",
        "the page uses k = 60 where the plan says 50",
        SPRING,
        "refuse",
        edit=sub("k: 50", "k: 60"),
        note="Only the plan comparison can see this; the page and the reference agree.",
    ),
    Mutation(
        "page-constant-readout",
        "provenance",
        "a readout fed by a free observable holding 0.04",
        SPRING,
        "refuse",
        edit=sub("value: extension,", "value: Synapse.observable(0.04),"),
    ),
    Mutation(
        "page-declared-constant-readout",
        "provenance",
        "a readout fed by a declared constant instead of the model",
        SPRING,
        "refuse",
        edit=sub("value: extension,", 'value: Synapse.constant(0.04, { label: "Extension", unit: "m" }),'),
    ),
    Mutation(
        "page-map-arithmetic",
        "provenance",
        "the model output is doubled with .map",
        SPRING,
        "refuse",
        edit=sub("value: extension,", "value: extension.map(function (x) { return x * 2; }),"),
    ),
    Mutation(
        "page-forged-observable",
        "provenance",
        "a hand-made object posing as an observable",
        SPRING,
        "refuse",
        edit=sub(
            "value: extension,",
            "value: { get: function () { return 0.04; }, set: function () {}, subscribe: function () { return function () {}; }, map: function () {} },",
        ),
    ),
    Mutation(
        "page-overwrite-readout",
        "provenance",
        "the readout text is overwritten after the Kit wrote it",
        SPRING,
        "refuse",
        edit=before_ready("document.querySelector('[data-synapse-readout]').textContent = '0.999 m';"),
    ),
    Mutation(
        "page-edit-note",
        "provenance",
        "the study note is edited to state a false number",
        SPRING,
        "refuse",
        edit=before_ready("document.querySelector('.syn-note').textContent = 'The spring stretches 0.9 m.';"),
    ),
    Mutation(
        "page-typed-number",
        "provenance",
        "a paragraph with a typed result",
        SPRING,
        "refuse",
        edit=before_ready(
            "var p = document.createElement('p'); p.textContent = 'Extension is 0.04 m'; env.stage.appendChild(p);"
        ),
    ),
    Mutation(
        "page-aria-number",
        "provenance",
        "a result hidden in an aria-label",
        SPRING,
        "refuse",
        edit=before_ready(
            "var p = document.createElement('p'); p.setAttribute('aria-label', 'Extension is 0.04 m'); env.stage.appendChild(p);"
        ),
    ),
    Mutation(
        "page-shadow-number",
        "provenance",
        "a result inside a shadow root (obfuscated call)",
        SPRING,
        "refuse",
        edit=before_ready(
            "var h = document.createElement('div'); env.stage.appendChild(h); h['attach' + 'Shadow']({ mode: 'open' }).innerHTML = '<p>0.04 m</p>';"
        ),
    ),
    Mutation(
        "page-late-number",
        "provenance",
        "a result inserted 1.2 s after load",
        SPRING,
        "refuse",
        edit=before_ready(
            "setTimeout(function () { var p = document.createElement('p'); p.textContent = 'Extension is 0.04 m'; env.stage.appendChild(p); }, 1200);"
        ),
    ),
    Mutation(
        "page-unbacked-copy",
        "provenance",
        "a Kit sentence states a number that no control or constant backs",
        SPRING,
        "refuse",
        edit=before_ready("Synapse.text(env, 'At 2 N the extension is 0.05 m.');"),
    ),
    Mutation(
        "page-redefine-kit",
        "provenance",
        "the page redefines window.Synapse",
        SPRING,
        "refuse",
        edit=before_ready(
            "Object.defineProperty(window, 'Synapse', { value: { audit: function () { return null; } } });"
        ),
    ),
    Mutation(
        "page-wrong-unit-label",
        "physics",
        "the readout is labelled kPa but shows pascals",
        PRESSURE,
        "refuse",
        edit=sub('unit: "kPa"', 'unit: "Pa"'),
        note="Readout units are page-declared and not compared with the model's output unit.",
    ),
    Mutation(
        "page-wrong-label",
        "physics",
        "the readout label says Load but shows the extension",
        SPRING,
        "refuse",
        edit=sub('label: "Extension"', 'label: "Load"'),
        known_miss=True,
        note="Meaning of a label is not machine-checkable here; the textbook citation and a person are the defence.",
    ),
    Mutation(
        "page-false-prose",
        "physics",
        "the study note claims the opposite of the physics, with no numbers",
        SPRING,
        "refuse",
        edit=sub("the extension is proportional to the load", "the extension is inversely proportional to the load"),
        known_miss=True,
        note="Prose is not verified. Only grounding to a textbook (P2) and review can address it.",
    ),
    # ── trust-path defects ─────────────────────────────────────────────────────────────────────────────────────────────────
    Mutation(
        "trust-fetch",
        "trust",
        "a literal fetch",
        SPRING,
        "refuse",
        edit=before_ready("fetch('https://example.invalid/x');"),
    ),
    Mutation(
        "trust-hidden-fetch",
        "trust",
        "a fetch built from string pieces",
        SPRING,
        "refuse",
        edit=before_ready("window['fe' + 'tch']('https://example.invalid/x');"),
    ),
    Mutation(
        "trust-eval",
        "trust",
        "eval hidden behind concatenation",
        SPRING,
        "refuse",
        edit=before_ready("window['ev' + 'al']('1+1');"),
    ),
    Mutation(
        "trust-navigate-literal",
        "trust",
        "location assignment on click",
        SPRING,
        "refuse",
        edit=before_ready(
            "document.addEventListener('click', function () { location.href = 'https://example.invalid/'; });"
        ),
    ),
    Mutation(
        "trust-navigate-obfuscated",
        "trust",
        "obfuscated navigation on click",
        SPRING,
        "refuse",
        edit=before_ready(
            "document.addEventListener('click', function () { window['loc' + 'ation']['hr' + 'ef'] = 'https://example.invalid/'; });"
        ),
    ),
    Mutation(
        "trust-second-csp",
        "trust",
        "a model-written permissive CSP",
        SPRING,
        "neutralise",
        edit=sub(
            '<meta name="viewport"',
            '<meta http-equiv="Content-Security-Policy" content="default-src *">\n<meta name="viewport"',
        ),
    ),
    Mutation(
        "trust-csp-in-comment",
        "trust",
        "a head tag inside a comment to switch the CSP off",
        SPRING,
        "neutralise",
        edit=sub("<head>", "<!-- <head> --><head>"),
    ),
    Mutation(
        "trust-remote-script",
        "trust",
        "a script loaded from another origin",
        SPRING,
        "refuse",
        edit=sub("<script>", '<script src="https://cdn.example.invalid/x.js"></script>\n<script>'),
    ),
    Mutation(
        "trust-canvas-text",
        "trust",
        "numbers drawn on a canvas",
        SPRING,
        "refuse",
        edit=before_ready(
            "var c = document.createElement('canvas'); env.stage.appendChild(c); c.getContext('2d').fillText('0.04 m', 0, 10);"
        ),
    ),
    Mutation(
        "trust-hidden-eval-in-timer",
        "trust",
        "a string passed to setTimeout",
        SPRING,
        "refuse",
        edit=before_ready("setTimeout('1+1', 10);"),
    ),
    # ── structure defects ──────────────────────────────────────────────────────────────────────────────────────────────────
    Mutation(
        "struct-undeclared-control",
        "structure",
        "a plain button the Kit did not make",
        SPRING,
        "refuse",
        edit=before_ready(
            "var b = document.createElement('button'); b.textContent = 'Go'; env.controls.appendChild(b);"
        ),
    ),
    Mutation(
        "struct-dead-control",
        "structure",
        "a second slider that feeds nothing",
        SPRING,
        "refuse",
        edit=before_ready('Synapse.slider(env, { id: "spare", label: "Spare", unit: "N", min: 0, max: 5, value: 1 });'),
    ),
    Mutation(
        "struct-self-moving-readout",
        "structure",
        "the load moves on a timer",
        SPRING,
        "refuse",
        edit=before_ready("setInterval(function () { load.set(Math.random() * 10); }, 80);"),
    ),
    Mutation(
        "struct-no-controls",
        "structure",
        "no control at all",
        SPRING,
        "refuse",
        edit=sub(
            'var load = Synapse.slider(env, { id: "load", label: "Load", unit: "N", min: 0, max: 10, value: 2, step: 0.1 });',
            'var load = Synapse.constant(2, { label: "Load", unit: "N" });',
        ),
    ),
    Mutation(
        "struct-throws",
        "structure",
        "the page throws before ready",
        SPRING,
        "refuse",
        edit=before_ready("throw new Error('boom');"),
    ),
    Mutation("struct-never-ready", "structure", "ready is never signalled", SPRING, "refuse", edit=sub(READY, "")),
    Mutation(
        "struct-overflow",
        "structure",
        "a 900 px wide element",
        SPRING,
        "refuse",
        edit=before_ready(
            "var w = document.createElement('div'); w.style.width = '900px'; w.style.height = '10px'; env.stage.appendChild(w);"
        ),
    ),
    # ── core component defects ─────────────────────────────────────────────────────────────────────────────────────────────
    Mutation(
        "comp-graph-free-observable",
        "provenance",
        "a graph fed by a free observable",
        OHM_GRAPH,
        "refuse",
        edit=sub("y: current,", "y: Synapse.observable(1),"),
    ),
    Mutation(
        "comp-graph-wrong-unit",
        "physics",
        "a graph labelled mA that plots amperes",
        OHM_GRAPH,
        "refuse",
        edit=sub('yUnit: "A"', 'yUnit: "mA"'),
    ),
    Mutation(
        "comp-table-wrong-unit",
        "physics",
        "a table column labelled V that records amperes",
        OHM_GRAPH,
        "refuse",
        edit=sub('label: "Current", unit: "A"', 'label: "Current", unit: "V"'),
    ),
    Mutation(
        "comp-forged-action",
        "trust",
        "a script-made button claiming to be a Kit action",
        OHM_GRAPH,
        "refuse",
        edit=sub(
            "Synapse.reset(env);",
            "Synapse.reset(env); var b = document.createElement('button'); b.textContent = 'Go'; b.setAttribute('data-synapse-action', 'reset'); env.controls.appendChild(b);",
        ),
    ),
    Mutation(
        "kit-ohm-graph-power",
        "physics",
        "Ohm's model returns V times R (seen through a graph and a table)",
        OHM_GRAPH,
        "refuse",
        kit_edit=patch_fn(["voltage", "resistance"], "{voltage}*{resistance}"),
    ),
    Mutation("neutral-ohm-graph", "neutral", "the unmodified graph, table and reset page", OHM_GRAPH, "accept"),
    # ── kit-guardian P1 review: attack pages (each was minted before the fixes) ────────────────────────────────────────────
    Mutation(
        "g-fullwidth-digits",
        "provenance",
        "a result in fullwidth digits",
        SPRING,
        "refuse",
        edit=sub("</body>", "<p>Answer: \uff14\uff12 m</p>\n</body>"),
    ),
    Mutation(
        "g-list-marker-copy",
        "provenance",
        "copy that starts with a number",
        SPRING,
        "refuse",
        edit=before_ready('Synapse.text(env, "42 m is the extension at full load.");'),
    ),
    Mutation(
        "g-newline-copy",
        "provenance",
        "copy with a number after a newline",
        SPRING,
        "refuse",
        edit=before_ready('Synapse.text(env, "Extension at full load:\\n42 m");'),
    ),
    Mutation(
        "g-step-context-copy",
        "provenance",
        "a quantity hidden behind the word step",
        SPRING,
        "refuse",
        edit=before_ready('Synapse.text(env, "The extension is step 42 m.");'),
    ),
    Mutation(
        "g-readout-label-mutation",
        "provenance",
        "the options object is changed after readout() and the label rewritten",
        SPRING,
        "refuse",
        edit=sub(
            'Synapse.readout(env, { label: "Extension", unit: "m", value: extension, digits: 3 });',
            'var ro = { label: "Extension", unit: "m", value: extension, digits: 3 }; var out = Synapse.readout(env, ro); ro.label = "Extension (at 10 N it is 42 m)"; out.previousSibling.textContent = ro.label;',
        ),
    ),
    Mutation(
        "g-note-mutation",
        "provenance",
        "the environment options are changed and the note rewritten",
        SPRING,
        "refuse",
        edit=lambda h: (
            h.replace("var env = Synapse.environment({", "var o = ({", 1)
            .replace(
                "  var load = Synapse.slider", "  var env = Synapse.environment(o);\n  var load = Synapse.slider", 1
            )
            .replace(
                READY,
                'o.note = "At 10 N the extension is 42 m."; document.querySelector(".syn-note").textContent = o.note;\n  '
                + READY,
                1,
            )
        ),
    ),
    Mutation(
        "g-table-column-swap",
        "provenance",
        "a table column's observable is swapped for a fake after creation (the Kit copied the columns, so Record still writes the verified value)",
        SPRING,
        "accept",
        edit=before_ready(
            'var cols = [{ label: "Load", unit: "N", value: load }, { label: "Extension", unit: "m", value: extension, digits: 3 }]; Synapse.table(env, { caption: "Results", columns: cols }); cols[1].value = { get: function () { return 42; } }; var rec = document.querySelector("[data-synapse-action=record]"); load.subscribe(function () { rec.click(); });'
        ),
    ),
    Mutation(
        "g-patch-regexp",
        "trust",
        "RegExp.prototype.test is patched to hide digits from the audit",
        SPRING,
        "refuse",
        edit=before_ready(
            'var t0 = RegExp.prototype.test; RegExp.prototype.test = function (s) { return this.source === "\\\\d" ? false : t0.call(this, s); }; var p = document.createElement("p"); p.textContent = "Answer: 42 m"; document.body.appendChild(p);'
        ),
        note="The patch itself is a no-op once the intrinsics are frozen; the typed number is then caught.",
    ),
    Mutation(
        "g-patch-flatmap",
        "trust",
        "Array.prototype.flatMap is emptied so owned mismatches vanish",
        SPRING,
        "refuse",
        edit=before_ready(
            'Array.prototype.flatMap = function () { return []; }; document.querySelector("h1").textContent = "The extension is 42 m";'
        ),
    ),
    Mutation(
        "g-ol-start",
        "provenance",
        "a number drawn by an ordered-list counter",
        SPRING,
        "refuse",
        edit=sub("</body>", '<ol start="42"><li>m is the extension at full load</li></ol>\n</body>'),
    ),
    Mutation(
        "g-syn-style-counter",
        "provenance",
        "a page makes its own stylesheet with the Kit's id to number a list by CSS counter",
        SPRING,
        "refuse",
        edit=lambda html: sub("</body>", '<ol><li>m is the extension at full load</li></ol>\n</body>')(
            sub("</head>", '<style id="syn-style">ol{counter-reset:list-item 41}</style>\n</head>')(html)
        ),
        note="added after the W3 review: the audit used to skip the CSS check for any style with the id syn-style",
    ),
    Mutation(
        "g-counter-style-at-rule",
        "provenance",
        "a number drawn by an @counter-style list marker",
        SPRING,
        "refuse",
        edit=lambda html: sub("</body>", '<style>@counter-style fx{system:fixed;symbols:"9.81"} ol{list-style-type:fx}</style><ol><li>m is the extension at full load</li></ol>\n</body>')(html),
        note="added after the W3 review: no stylesheet check named @counter-style",
    ),
    Mutation(
        "g-aria-valuenow",
        "provenance",
        "a number spoken through aria-valuenow",
        SPRING,
        "refuse",
        edit=sub(
            "</body>",
            '<div role="meter" aria-label="Extension" aria-valuemin="0" aria-valuemax="100" aria-valuenow="42"></div>\n</body>',
        ),
    ),
    Mutation(
        "g-canvas-concat",
        "trust",
        "canvas text built from string pieces",
        SPRING,
        "refuse",
        edit=before_ready(
            'var c = document.createElement("can" + "vas"); var x = c["get" + "Context"]("2d"); x["fill" + "Text"]("Answer: 42 m", 4, 28); env.stage.appendChild(c);'
        ),
    ),
    Mutation(
        "g-css-background-svg",
        "trust",
        "a number drawn as a CSS background image built from pieces",
        SPRING,
        "refuse",
        edit=before_ready(
            'var d = document.createElement("div"); d.style.height = "40px"; d.style.backgroundImage = "url(\\"da" + "ta:ima" + "ge/svg+xml,%3Csvg xmlns=%27http:%2F%2Fwww.w3.org%2F2000%2Fsvg%27%3E%3Ctext y=%2720%27%3E42 m%3C%2Ftext%3E%3C%2Fsvg%3E\\")"; env.stage.appendChild(d);'
        ),
    ),
    Mutation(
        "g-input-unit-kg",
        "physics",
        "a mass slider (kg) feeds the force input of Hooke's law",
        SPRING,
        "refuse",
        edit=sub('label: "Load", unit: "N"', 'label: "Mass", unit: "kg"'),
    ),
    Mutation(
        "g-constant-readout-extra",
        "physics",
        "an extra readout of a bare constant beside the real one",
        SPRING,
        "refuse",
        edit=before_ready(
            'Synapse.readout(env, { label: "Extension at 10 N", unit: "m", value: Synapse.constant(42, { label: "x10", unit: "m" }) });'
        ),
    ),
    Mutation(
        "g-timer-60s-forge",
        "provenance",
        "the readout is overwritten after 60 seconds",
        SPRING,
        "refuse",
        edit=before_ready(
            'setTimeout(function () { document.querySelector("output").textContent = "42.000 m"; }, 60000);'
        ),
        known_miss=True,
        note="The harness cannot wait that long. The Kit's runtime self-check catches it in the student's browser and the host hides the Environment (tests: eval/l6/test_guardian_attacks.py).",
    ),
    Mutation(
        "g-coarse-pointer-forge",
        "provenance",
        "the readout is overwritten only on touch screens",
        SPRING,
        "refuse",
        edit=before_ready(
            'if (matchMedia("(pointer: coarse)").matches) document.querySelector("output").textContent = "42.000 m";'
        ),
        known_miss=True,
        note="The verification browser has a fine pointer. The runtime self-check catches it on the student's phone.",
    ),
    Mutation(
        "g-patch-observable-get",
        "provenance",
        "an observable's get() is replaced before the model is built",
        SPRING,
        "accept",
        edit=sub(
            "  var extension = Synapse.hookes",
            "  var g0 = load.get; load.get = function () { return g0() * 9.81; };\n  var extension = Synapse.hookes",
        ),
        note="Observables are frozen, so the assignment does nothing and the page behaves normally.",
    ),
    # ── neutral controls: harmless edits that must be accepted (false-positive measure) ─────────────────────────────────────
    Mutation(
        "neutral-title",
        "neutral",
        "a different title and note",
        SPRING,
        "accept",
        edit=sub('title: "Why does a spring stretch?"', 'title: "A spring and a load"'),
    ),
    Mutation(
        "neutral-default", "neutral", "a different starting load", SPRING, "accept", edit=sub("value: 2,", "value: 5,")
    ),
    Mutation(
        "neutral-digits",
        "neutral",
        "a different number of digits",
        SPRING,
        "accept",
        edit=sub("digits: 3", "digits: 2"),
    ),
    Mutation(
        "neutral-backed-sentence",
        "neutral",
        "a sentence that states the spring constant",
        SPRING,
        "accept",
        edit=before_ready("Synapse.text(env, 'The spring constant is 50 N/m.');"),
    ),
    Mutation(
        "neutral-step-marker",
        "neutral",
        "a sentence with a step marker",
        SPRING,
        "accept",
        edit=before_ready("Synapse.text(env, 'Step 2: slide the load to its largest value.');"),
    ),
    Mutation(
        "neutral-ohm-range",
        "neutral",
        "a different resistance range",
        OHM,
        "accept",
        edit=sub("min: 1, max: 20", "min: 2, max: 20"),
    ),
    # ── the drag path (W4): masses a student drags or presses. The model-free verifier really drags them (L2, `drag_dead`). ──────────────────────
    Mutation(
        "drag-pointerdown-blocked",
        "structure",
        "a page swallows every pointerdown, so the masses cannot be dragged",
        MASSES,
        "refuse",
        edit=before_ready('document.addEventListener("pointerdown", function (e) { e.stopImmediatePropagation(); }, true);'),
    ),
    Mutation(
        "drag-click-blocked",
        "structure",
        "a page swallows every click, so a mass cannot be pressed from the keyboard",
        MASSES,
        "refuse",
        edit=before_ready('document.addEventListener("click", function (e) { e.stopImmediatePropagation(); }, true);'),
    ),
    Mutation(
        "drag-forged-mass",
        "trust",
        "a page makes its own draggable mass with the Kit's action marker",
        MASSES,
        "refuse",
        edit=sub("</body>", '<button data-synapse-action="drag" data-synapse-drag="load">Mass Z</button>\n</body>'),
    ),
    Mutation(
        "drag-mass-label-number",
        "provenance",
        "a mass whose accessible name carries a number the Kit did not set",
        MASSES,
        "refuse",
        edit=before_ready('document.querySelector("[data-synapse-drag=load]").setAttribute("aria-label", "Mass A weighs 9.81 N");'),
    ),
    Mutation(
        "drag-block-all-but-first-mass",
        "structure",
        "a page blocks the pointer on every mass except the first, so only Mass A would pass a one-mass check",
        MASSES,
        "refuse",
        edit=before_ready(
            'document.addEventListener("pointerdown", function (e) { var t = e.target; if (t && t.getAttribute && t.getAttribute("data-synapse-drag") && t.textContent !== "A") e.stopImmediatePropagation(); }, true);'
        ),
    ),
    Mutation(
        "drag-block-touch-only",
        "structure",
        "a page blocks a finger on the masses but lets the mouse through",
        MASSES,
        "refuse",
        edit=before_ready('document.addEventListener("pointerdown", function (e) { if (e.pointerType === "touch") e.stopImmediatePropagation(); }, true);'),
    ),
    Mutation(
        "drag-hide-from-harness",
        "structure",
        "a page removes the masses' drag marker and swallows the pointer, so a harness that finds masses by the marker finds none",
        MASSES,
        "refuse",
        edit=before_ready(
            'Array.from(document.querySelectorAll("[data-synapse-drag]")).forEach(function (m) { m.removeAttribute("data-synapse-drag"); });'
            'document.addEventListener("pointerdown", function (e) { e.stopImmediatePropagation(); }, true);'
        ),
    ),
    Mutation(
        "drag-mass-hidden",
        "structure",
        "a page hides one mass, so the hanger holds a mass the picture does not show",
        MASSES,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelectorAll("[data-synapse-drag]")[1].style.display = "none"; }, 20);'),
    ),
    Mutation(
        "drag-mass-moved",
        "structure",
        "a page moves one mass far off its place with a transform",
        MASSES,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelectorAll("[data-synapse-drag]")[2].style.transform = "translate(700px, 0)"; }, 20);'),
    ),
    Mutation(
        "drag-off-step-load-set",
        "neutral",
        "a script sets the load to a value between two masses; the control snaps it to a whole number of masses",
        MASSES,
        "accept",
        edit=before_ready("c_load.set(2.9);"),
    ),
    Mutation(
        "scene-bound-to-free-observable",
        "provenance",
        "the spring picture is bound to a number the page typed, not the model's output",
        MASSES,
        "refuse",
        edit=sub("extension: m_spring, full: 0.25", "extension: Synapse.observable(0.1), full: 0.25"),
    ),
    Mutation(
        "scene-bound-to-the-control",
        "provenance",
        "the spring picture is bound to the load control instead of the extension",
        MASSES,
        "refuse",
        edit=sub("extension: m_spring, full: 0.25", "extension: c_load, full: 0.25"),
    ),
    Mutation(
        "scene-bound-to-a-map",
        "provenance",
        "the spring picture is bound to arithmetic the page wrote on the model's output",
        MASSES,
        "refuse",
        edit=sub("extension: m_spring, full: 0.25", "extension: m_spring.map(function (v) { return v * 2; }), full: 0.25"),
    ),
    Mutation(
        "scene-redrawn",
        "provenance",
        "a page redraws the spring so it shows a stretch the model did not compute",
        MASSES,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-scene polyline").setAttribute("points", "0,0 160,250"); }, 20);'),
    ),
    Mutation(
        "scene-relabelled",
        "provenance",
        "a page rewrites the spring's text description",
        MASSES,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-scene").setAttribute("aria-label", "A spring that is not stretched at all."); }, 20);'),
    ),
    Mutation(
        "scene-hidden",
        "provenance",
        "a page hides the spring picture",
        MASSES,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-scene").style.visibility = "hidden"; }, 20);'),
    ),
    Mutation(
        "drag-block-touch-all-but-first",
        "structure",
        "a page blocks a finger on every mass except Mass A",
        MASSES,
        "refuse",
        edit=before_ready(
            'document.addEventListener("pointerdown", function (e) { var t = e.target; if (e.pointerType === "touch" && t && t.getAttribute && t.getAttribute("data-synapse-drag") && t.textContent !== "A") e.stopImmediatePropagation(); }, true);'
        ),
    ),
    Mutation(
        "drag-block-keys-all-but-first",
        "structure",
        "a page blocks the keyboard on every mass except Mass A",
        MASSES,
        "refuse",
        edit=before_ready(
            '["keydown", "keyup"].forEach(function (n) { document.addEventListener(n, function (e) { var t = e.target; if (t && t.getAttribute && t.getAttribute("data-synapse-drag") && t.textContent !== "A") { e.preventDefault(); e.stopImmediatePropagation(); } }, true); });'
        ),
    ),
    Mutation(
        "drag-hanger-faded-by-css",
        "structure",
        "a style rule fades the hanger out, so hung masses cannot be seen while the control counts them",
        MASSES,
        "refuse",
        edit=sub("</body>", "<style>.syn-hanger{opacity:.02}</style></body>"),
    ),
    Mutation(
        "drag-hung-mass-pushed-offscreen-by-css",
        "structure",
        "a style rule pushes the third mass on the hanger off the screen, so the hanger shows one mass fewer than the control",
        MASSES,
        "refuse",
        edit=sub("</body>", "<style>.syn-hanger .syn-mass:nth-child(3){transform:translateX(-300vw)}</style></body>"),
    ),
    Mutation(
        "drag-hanger-collapsed-by-css",
        "structure",
        "a style rule collapses the hanger to nothing, so a mass can hardly be dropped on it",
        MASSES,
        "refuse",
        edit=sub("</body>", "<style>.syn-hanger{height:0;min-height:0;padding:0;border:0;overflow:visible}</style></body>"),
    ),
    Mutation(
        "drag-captions-swapped",
        "structure",
        "a page swaps the Tray and Hanger captions, so masses labelled as hung are in the tray",
        MASSES,
        "refuse",
        edit=before_ready(
            'setInterval(function () { var c = document.querySelectorAll(".syn-cap"); if (c.length === 2) { var a = c[0].textContent; c[0].textContent = c[1].textContent; c[1].textContent = a; } }, 20);'
        ),
    ),
    Mutation(
        "drag-overlay-pointer-transparent",
        "structure",
        "a page lays a pointer-transparent white sheet over the whole bench, so the masses cannot be seen but can still be pressed",
        MASSES,
        "refuse",
        edit=sub("</body>", '<div style="position:fixed;left:0;top:0;right:0;bottom:0;background:#fff;pointer-events:none;z-index:9"></div></body>'),
    ),
    Mutation(
        "scene-coil-stroke-removed",
        "provenance",
        "a page removes the colour of the spring's coil, so no spring is drawn",
        MASSES,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-scene polyline").setAttribute("stroke", "none"); }, 20);'),
    ),
    Mutation(
        "scene-squashed-by-css",
        "provenance",
        "a style rule draws the spring at a quarter of its length",
        MASSES,
        "refuse",
        edit=sub("</body>", "<style>.syn-scene polyline,.syn-scene rect{transform:scale(1,.25)}</style></body>"),
    ),
    Mutation(
        "scene-stage-hidden-by-css",
        "provenance",
        "a style rule hides the whole stage the spring is drawn on",
        MASSES,
        "refuse",
        edit=sub("</body>", "<style>.syn-stage{display:none}</style></body>"),
    ),
    Mutation(
        "scene-draws-another-model-instance",
        "provenance",
        "the spring is drawn from a second Hooke's law model with a spring constant ten times larger than the one the readouts use",
        MASSES,
        "refuse",
        edit=sub("extension: m_spring, full: 0.25", "extension: Synapse.hookes({ k: 500.0, load: c_load }), full: 0.25"),
    ),
    Mutation(
        "scene-scale-huge",
        "provenance",
        "the spring is given a drawing scale a thousand times too large, so it never visibly moves",
        MASSES,
        "refuse",
        edit=sub("full: 0.25", "full: 1000"),
    ),
    Mutation(
        "valve-pointer-swallowed",
        "structure",
        "a page swallows every pointerdown, so the stopcock cannot be held",
        TITR,
        "refuse",
        edit=before_ready('document.addEventListener("pointerdown", function (e) { e.stopImmediatePropagation(); }, true);'),
    ),
    Mutation(
        "valve-click-swallowed",
        "structure",
        "a page swallows every click, so the stopcock cannot be tapped or pressed from the keyboard",
        TITR,
        "refuse",
        edit=before_ready('document.addEventListener("click", function (e) { e.stopImmediatePropagation(); }, true);'),
    ),
    Mutation(
        "valve-keys-swallowed",
        "structure",
        "a page swallows the keyboard, so the stopcock cannot be pressed with Enter or Space",
        TITR,
        "refuse",
        edit=before_ready('["keydown", "keyup"].forEach(function (n) { document.addEventListener(n, function (e) { e.preventDefault(); e.stopImmediatePropagation(); }, true); });'),
    ),
    Mutation(
        "valve-finger-swallowed",
        "structure",
        "a page blocks a finger on the stopcock but lets the mouse through",
        TITR,
        "refuse",
        edit=before_ready('document.addEventListener("pointerdown", function (e) { if (e.pointerType === "touch") e.stopImmediatePropagation(); }, true);'),
    ),
    Mutation(
        "valve-never-stops",
        "structure",
        "a page swallows pointerup and pointercancel, so the stopcock keeps running after the pointer is lifted",
        TITR,
        "refuse",
        edit=before_ready('["pointerup", "pointercancel"].forEach(function (n) { document.addEventListener(n, function (e) { e.stopImmediatePropagation(); }, true); });'),
    ),
    Mutation(
        "valve-forged",
        "trust",
        "a page makes its own stopcock with the Kit's action marker",
        TITR,
        "refuse",
        edit=sub("</body>", '<button data-synapse-action="valve" data-synapse-valve="vb">Stopcock</button>\n</body>'),
    ),
    Mutation(
        "valve-label-number",
        "provenance",
        "a stopcock whose accessible name carries a number the Kit did not set",
        TITR,
        "refuse",
        edit=before_ready('document.querySelector("[data-synapse-valve=vb]").setAttribute("aria-label", "Stopcock, 25 cm3 run in");'),
    ),
    Mutation(
        "valve-hidden",
        "structure",
        "a page hides the stopcock",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector("[data-synapse-valve=vb]").style.display = "none"; }, 20);'),
    ),
    Mutation(
        "valve-shrunk-by-css",
        "structure",
        "a style rule shrinks the stopcock below a finger's size",
        TITR,
        "refuse",
        edit=sub("</body>", "<style>.syn-valve{max-width:20px;min-width:0;padding:0;overflow:hidden}</style></body>"),
    ),
    Mutation(
        "eye-pointer-swallowed",
        "structure",
        "a page swallows the pointer on the eye, so it cannot be dragged",
        TITR,
        "refuse",
        edit=before_ready('document.addEventListener("pointerdown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) e.stopImmediatePropagation(); }, true);'),
    ),
    Mutation(
        "eye-keys-swallowed",
        "structure",
        "a page swallows the keyboard on the eye, so it cannot be moved by the arrow keys",
        TITR,
        "refuse",
        edit=before_ready('document.addEventListener("keydown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);'),
    ),
    Mutation(
        "eye-forged",
        "trust",
        "a page makes its own eye with the Kit's action marker",
        TITR,
        "refuse",
        edit=sub("</body>", '<button data-synapse-action="eye" data-synapse-eye>Eye</button>\n</body>'),
    ),
    Mutation(
        "eye-moved",
        "provenance",
        "a page moves the eye away from where the Kit put it",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector("[data-synapse-eye]").style.top = "2%"; }, 20);'),
    ),
    Mutation(
        "eye-shifted-by-css",
        "provenance",
        "a style rule shifts the eye off its line of sight with a margin",
        TITR,
        "refuse",
        edit=sub("</body>", "<style>.syn-eye{margin-top:200px}</style></body>"),
    ),
    Mutation(
        "burette-liquid-redrawn",
        "provenance",
        "a page redraws the liquid in the burette",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-titration rect[fill=\\"var(--syn-liquid)\\"]").setAttribute("y", "40"); }, 20);'),
    ),
    Mutation(
        "flask-colour-forced",
        "provenance",
        "a page keeps the flask colourless at the end point",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-titration path").setAttribute("fill", "var(--syn-card)"); }, 20);'),
    ),
    Mutation(
        "burette-relabelled",
        "provenance",
        "a page rewrites the burette picture's text description",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-titration").setAttribute("aria-label", "A full burette above a pink flask."); }, 20);'),
    ),
    Mutation(
        "burette-hidden",
        "provenance",
        "a page hides the burette picture",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-titration").style.visibility = "hidden"; }, 20);'),
    ),
    Mutation(
        "burette-squashed-by-css",
        "provenance",
        "a style rule squashes the burette picture",
        TITR,
        "refuse",
        edit=sub("</body>", "<style>.syn-titration{transform:scale(1,.3)}</style></body>"),
    ),
    Mutation(
        "burette-faded-by-css",
        "provenance",
        "a style rule fades the whole burette picture out",
        TITR,
        "refuse",
        edit=sub("</body>", "<style>.syn-titr-frame{opacity:.02}</style></body>"),
    ),
    Mutation(
        "meniscus-moved",
        "provenance",
        "a page moves the meniscus line away from the liquid's surface",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector("[data-synapse-meniscus]").setAttribute("y1", "20"); }, 20);'),
    ),
    Mutation(
        "eye-sentence-rewritten",
        "provenance",
        "a page rewrites the sentence that says how the eye reads the meniscus",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector("[data-synapse-eye-status]").textContent = "Your eye is level with the meniscus, so this is a fair reading."; }, 20);'),
    ),
    Mutation(
        "scene-added-free-observable",
        "provenance",
        "the burette is bound to a number the page typed, not the control",
        TITR,
        "refuse",
        edit=sub("added: c_vb", "added: Synapse.observable(10)"),
    ),
    Mutation(
        "scene-endpoint-free-observable",
        "provenance",
        "the indicator changes at a number the page typed, not the end-point model's output",
        TITR,
        "refuse",
        edit=sub("endpoint: m_endpoint", "endpoint: Synapse.observable(20)"),
    ),
    Mutation(
        "scene-endpoint-other-model",
        "provenance",
        "the indicator changes where the concentration model says, not the end-point model",
        TITR,
        "refuse",
        edit=sub("endpoint: m_endpoint", "endpoint: m_alkali"),
    ),
    Mutation(
        "scene-endpoint-is-the-control",
        "provenance",
        "the indicator is bound to the volume run in itself",
        TITR,
        "refuse",
        edit=sub("endpoint: m_endpoint", "endpoint: c_vb"),
    ),
    Mutation(
        "burette-capacity-too-small",
        "provenance",
        "the burette is given a capacity below what the control can run in",
        TITR,
        "refuse",
        edit=sub("full: 50.0", "full: 30"),
    ),
    Mutation(
        "burette-capacity-huge",
        "provenance",
        "the burette is given a capacity so large it never visibly empties",
        TITR,
        "refuse",
        edit=sub("full: 50.0", "full: 1000"),
    ),
    Mutation(
        "endpoint-follows-the-control",
        "provenance",
        "the end point is fed by the control, so the flask turns pink from the first position",
        TITR,
        "refuse",
        edit=sub('va: k_va', 'va: c_vb'),
    ),
    Mutation(
        "endpoint-from-another-acid-volume",
        "provenance",
        "the end point is fed by a different acid volume than the concentration uses",
        TITR,
        "refuse",
        edit=sub('va: k_va', 'va: Synapse.constant(12.5, { label: "Other acid", unit: "cm3" })'),
    ),
    Mutation(
        "endpoint-other-acid-strength",
        "provenance",
        "the end point uses another acid concentration than the concentration readout",
        TITR,
        "refuse",
        edit=sub('ma: 0.1, mb: k_mb', 'ma: 0.2, mb: k_mb'),
    ),
    Mutation(
        "css-pink-flask",
        "provenance",
        "a style rule paints the flask pink whatever the volume",
        TITR,
        "refuse",
        edit=sub('</body>', '<style>.syn-titration path{fill:var(--syn-indicator)}</style></body>'),
    ),
    Mutation(
        "css-kit-colour-redefined",
        "provenance",
        "a page redefines the Kit's indicator colour so the flask never turns pink",
        TITR,
        "refuse",
        edit=sub('</body>', '<style>:root{--syn-indicator:#f7f8f4}</style></body>'),
    ),
    Mutation(
        "css-liquid-pinned-full",
        "provenance",
        "a style rule pins the burette's liquid at full",
        TITR,
        "refuse",
        edit=sub('</body>', '<style>.syn-titration rect:nth-of-type(3){y:20px;height:130px}</style></body>'),
    ),
    Mutation(
        "css-note-hidden",
        "structure",
        "a style rule hides the eye's only text",
        TITR,
        "refuse",
        edit=sub('</body>', '<style>.syn-eye-note{display:none}</style></body>'),
    ),
    Mutation(
        "svg-flask-fill-opacity",
        "provenance",
        "a page makes the flask invisible with an SVG attribute",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-titration path").setAttribute("fill-opacity", "0"); }, 20);'),
    ),
    Mutation(
        "svg-liquid-visibility",
        "provenance",
        "a page hides the burette's liquid with an SVG attribute",
        TITR,
        "refuse",
        edit=before_ready('setInterval(function () { document.querySelector(".syn-titration rect").setAttribute("visibility", "hidden"); }, 20);'),
    ),
    Mutation(
        "svg-opaque-shape-over-the-flask",
        "provenance",
        "a page adds an opaque shape inside the picture, over the flask",
        TITR,
        "refuse",
        edit=before_ready('var r = document.createElementNS("http://www.w3.org/2000/svg", "rect"); r.setAttribute("x", "0"); r.setAttribute("y", "190"); r.setAttribute("width", "110"); r.setAttribute("height", "90"); r.setAttribute("fill", "#d6336c"); document.querySelector(".syn-titration").appendChild(r);'),
    ),
    Mutation(
        "popover-sheet",
        "structure",
        "a page opens a popover (the top layer) to cover the picture",
        TITR,
        "refuse",
        edit=before_ready('var d = document.createElement("div"); d.setAttribute("popover", "manual"); d.textContent = "x"; document.body.appendChild(d); d.showPopover();'),
    ),
    Mutation(
        "kit-sheet-rule-inserted",
        "structure",
        "a page inserts a rule into the Kit's own stylesheet through the CSSOM (its text is untouched)",
        TITR,
        "refuse",
        edit=before_ready('document.getElementById("syn-style").sheet.insertRule(".syn-readout{display:none}", 0);'),
    ),
    Mutation(
        "constructed-stylesheet",
        "structure",
        "a page adopts a constructed stylesheet",
        TITR,
        "refuse",
        edit=before_ready('var sh = new CSSStyleSheet(); sh.replaceSync(".syn-titration{opacity:.02}"); document.adoptedStyleSheets = [sh];'),
    ),
    Mutation(
        "decoy-eye-sentence-and-dead-eye",
        "structure",
        "a hidden decoy sentence that always says what the harness wants, with the real eye dead",
        TITR,
        "refuse",
        edit=sub('<main', '<p hidden data-synapse-eye-status>above below level</p><main') if False else before_ready('var p = document.createElement("p"); p.hidden = true; p.setAttribute("data-synapse-eye-status", ""); p.textContent = "above below level"; document.body.insertBefore(p, document.body.firstChild); document.addEventListener("pointerdown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) e.stopImmediatePropagation(); }, true); document.addEventListener("keydown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);'),
    ),
    Mutation("neutral-no-edit-titration", "neutral", "the unmodified titration bench", TITR, "accept"),
    Mutation("neutral-no-edit-masses", "neutral", "the unmodified mass bench", MASSES, "accept"),
    Mutation("neutral-no-edit-spring", "neutral", "the unmodified spring", SPRING, "accept"),
    Mutation("neutral-no-edit-ohm", "neutral", "the unmodified Ohm page", OHM, "accept"),
    Mutation("neutral-no-edit-pressure", "neutral", "the unmodified pressure page", PRESSURE, "accept"),
]
