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
    Mutation("neutral-no-edit-spring", "neutral", "the unmodified spring", SPRING, "accept"),
    Mutation("neutral-no-edit-ohm", "neutral", "the unmodified Ohm page", OHM, "accept"),
    Mutation("neutral-no-edit-pressure", "neutral", "the unmodified pressure page", PRESSURE, "accept"),
]
