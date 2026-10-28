"""The offline single-file export (P7): one HTML file that carries a stored Environment AND the Kit it was verified against, for a school PC with no network.

It is a different artifact from what the API serves, so it is built with care about what it must not weaken:
* it is built only from a block that came through the delivery gate (`deliver`), never from a raw row;
* the file carries the SHA-256 of the Environment's page and of the Kit bundle, and its own script checks both before anything runs; a mismatch shows a plain
  message and runs nothing, exactly as the web app refuses a block whose hash is wrong (hard constraint 1);
* the Environment still runs in `<iframe sandbox="allow-scripts">`, with no `allow-same-origin` (hard constraint 2). The Kit is placed inline in the frame's own
  document because an opaque-origin frame has no `/vendor/` to load it from; its bytes are the hashed bytes;
* the provenance (label, lane, source, what was checked, its limits) is printed in the file, because a file leaves our UI behind (hard constraint 11).
"""

from __future__ import annotations

import hashlib
import html as htmllib
import json
import re

from api.evidence.titles import citation_text
from api.schema.generated import EnvironmentBlock

LANE_TEXT = {
    "instantiate": "a stored Environment reused as it was",
    "compose": "planned for a question and assembled from audited Kit components",
    "free": "written whole by a model, not built on the Kit",
}
LABEL_TEXT = {
    "kit-verified": "Kit verified",
    "model-checked": "Checked by code, no verified textbook source",
    "reviewed": "Reviewed by a person",
    "canonical": "Canonical",
}


class ExportRefused(Exception):
    """The page cannot be exported safely (the Kit tag is not where it must be, or the Kit contains a script terminator)."""


def _kit_tag(version: str) -> str:
    return f'<script src="/vendor/kit/{version}/core.js"></script>'


def _json_for_script(value: object) -> str:
    """JSON that is safe inside a <script> element: every `<` becomes a JSON escape, so `</script>` and `<!--` cannot appear."""
    return json.dumps(value, ensure_ascii=True).replace("<", "\\u003c")



# ── the lab report inside an offline file (W5b follow-up, D-56) ─────────────────────────────────────────────────────────────────
# The web app builds the lab report from what the Kit tells the host (`synapse_lab`). A saved file has no web app, so its own shell does the same, in a few lines of
# plain script. It trusts nothing that crosses the frame boundary: only the frame this file made may speak, every size is re-checked (the same limits as
# `web/lib/sandbox.ts`), and everything is written with textContent, never as markup. The student's own words stay in the file's page and go nowhere.

_LAB_CSS = """
  #lab { margin-top: 1rem; padding: 1rem; border: 1px solid #8884; border-radius: 12px; display: grid; gap: .75rem; }
  #lab label { display: grid; gap: .25rem; font-weight: 600; }
  #lab textarea { font: inherit; font-weight: 400; min-height: 4.5rem; padding: .5rem; border-radius: 8px; border: 1px solid #8886; }
  #lab table { border-collapse: collapse; width: 100%; font-size: .9rem; }
  #lab th, #lab td { text-align: left; border-bottom: 1px solid #8884; padding: .25rem .5rem; }
  #lab .actions { display: flex; flex-wrap: wrap; gap: .5rem; }
  #lab .actions button { min-height: 44px; min-width: 44px; padding: 0 1rem; font: inherit; font-weight: 600; border-radius: 12px; border: 1px solid #8886; cursor: pointer; }
  #lab[hidden] { display: none; }
  #labprint { display: none; }
  @media print {
    body * { visibility: hidden; }
    #lab, #lab * { visibility: visible; }
    #lab { position: absolute; left: 0; top: 0; width: 100%; border: 0; }
    #lab h2, #labbody, #lab label, #lab .actions, #labnote, #labfoot { display: none; }
    #labprint { display: block; white-space: pre-wrap; font: 12pt/1.5 system-ui, sans-serif; }
  }
"""

_LAB_HTML = """<section id="lab" aria-label="Lab report" hidden>
<h2>Lab report</h2>
<div id="labbody"></div>
<label>Observations<textarea id="lab-observations" maxlength="1500" placeholder="What did you see happen as you changed it?"></textarea></label>
<label>Discussion<textarea id="lab-discussion" maxlength="1500" placeholder="Why do you think it happened? Did the results match the hypothesis?"></textarea></label>
<label>Conclusion<textarea id="lab-conclusion" maxlength="1500" placeholder="State what the experiment shows, in one or two sentences."></textarea></label>
<div class="actions">
<button type="button" id="labcopy">Copy report</button>
<button type="button" id="labsave">Download lab report</button>
<button type="button" id="labprintbtn">Print or save as PDF</button>
</div>
<p id="labnote" role="status" aria-live="polite"></p>
<p id="labfoot">The experiment, procedure and results come from the model you used. The observations, discussion and conclusion are your own words: they stay in this file and are not checked.</p>
<div id="labprint" aria-hidden="true"></div>
</section>"""

_LAB_JS = r"""
  var LAB = { experiment: null, steps: null, table: null }, labTitle = "", labClosed = false;
  var labBox = { observations: document.getElementById("lab-observations"), discussion: document.getElementById("lab-discussion"), conclusion: document.getElementById("lab-conclusion") };
  var labEl = document.getElementById("lab"), labBody = document.getElementById("labbody"), labNote = document.getElementById("labnote"), labPrint = document.getElementById("labprint");
  function isStr(v, max) { return typeof v === "string" && v.length <= max; }
  function strs(v, count, max) { if (!Array.isArray(v) || v.length > count) return null; for (var i = 0; i < v.length; i++) if (!isStr(v[i], max)) return null; return v; }
  function parseLab(d) {
    var i, j, f, c, r;
    if (d.part === "experiment") {
      if (!Array.isArray(d.fields) || d.fields.length > 8) return null;
      var fields = [];
      for (i = 0; i < d.fields.length; i++) { f = d.fields[i]; if (!Array.isArray(f) || f.length !== 2 || !isStr(f[0], 80) || !isStr(f[1], 400)) return null; fields.push([f[0], f[1]]); }
      return { part: "experiment", fields: fields };
    }
    if (d.part === "steps") { var st = strs(d.steps, 8, 300); return st ? { part: "steps", steps: st } : null; }
    if (d.part === "table") {
      if (!isStr(d.caption, 120) || !Array.isArray(d.columns) || d.columns.length < 1 || d.columns.length > 6 || !Array.isArray(d.rows) || d.rows.length > 30) return null;
      var cols = [], rows = [];
      for (i = 0; i < d.columns.length; i++) { c = d.columns[i]; if (typeof c !== "object" || c === null || !isStr(c.label, 60) || !isStr(c.unit, 16)) return null; cols.push({ label: c.label, unit: c.unit }); }
      for (j = 0; j < d.rows.length; j++) { r = strs(d.rows[j], cols.length, 40); if (!r || r.length !== cols.length) return null; rows.push(r); }
      return { part: "table", caption: d.caption, columns: cols, rows: rows };
    }
    return null;
  }
  function labHas() { return LAB.experiment !== null || LAB.steps !== null || (LAB.table !== null && LAB.table.columns.length > 0); }
  function labText() {
    var out = ["Lab report: " + labTitle, ""], i;
    if (LAB.experiment) for (i = 0; i < LAB.experiment.length; i++) out.push(LAB.experiment[i][0] + ": " + LAB.experiment[i][1]);
    if (LAB.steps && LAB.steps.length) { out.push("", "Procedure"); for (i = 0; i < LAB.steps.length; i++) out.push((i + 1) + ". " + LAB.steps[i]); }
    if (LAB.table) {
      out.push("", "Results: " + LAB.table.caption);
      out.push(LAB.table.columns.map(function (c) { return c.label + " (" + c.unit + ")"; }).join(" | "));
      if (LAB.table.rows.length === 0) out.push("(no rows recorded yet)");
      LAB.table.rows.forEach(function (row) { out.push(row.join(" | ")); });
    }
    out.push("", "Observations", labBox.observations.value.trim() || "(not written yet)");
    out.push("", "Discussion", labBox.discussion.value.trim() || "(not written yet)");
    out.push("", "Conclusion", labBox.conclusion.value.trim() || "(not written yet)");
    out.push("", "The experiment, procedure and results above come from the model you used. The observations, discussion and conclusion are your own words.");
    return out.join("\n");
  }
  function el(tag, text, parent) { var e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (parent) parent.appendChild(e); return e; }
  function labDraw() {
    labEl.hidden = !labHas();
    labBody.textContent = "";
    if (LAB.experiment) { var dl = el("dl", undefined, labBody); LAB.experiment.forEach(function (f) { el("dt", f[0], dl).style.fontWeight = "600"; el("dd", f[1], dl); }); }
    if (LAB.steps && LAB.steps.length) { el("p", "Procedure", labBody).style.fontWeight = "600"; var ol = el("ol", undefined, labBody); LAB.steps.forEach(function (s) { el("li", s, ol); }); }
    if (LAB.table) {
      el("p", "Results: " + LAB.table.caption, labBody).style.fontWeight = "600";
      if (LAB.table.rows.length === 0) el("p", "No rows yet. Press Record in the model to add a row of your results.", labBody);
      else {
        var box = el("div", undefined, labBody); box.style.overflowX = "auto";
        var t = el("table", undefined, box), hr = el("tr", undefined, el("thead", undefined, t)), tb = el("tbody", undefined, t);
        LAB.table.columns.forEach(function (c) { var th = el("th", c.label + " (" + c.unit + ")", hr); th.scope = "col"; });
        LAB.table.rows.forEach(function (row) { var tr = el("tr", undefined, tb); row.forEach(function (cell) { el("td", cell, tr); }); });
      }
    }
    labPrint.textContent = labText();
  }
  function labShut() { labReset(""); labClosed = true; }
  function labReset(title) {
    LAB = { experiment: null, steps: null, table: null }; labTitle = title || ""; labClosed = false;
    for (var k in labBox) labBox[k].value = "";
    labNote.textContent = ""; labDraw();
  }
  function labAccept(data) {
    if (labClosed) return;
    var part = parseLab(data);
    if (!part) return;
    if (part.part === "experiment") LAB.experiment = part.fields; else if (part.part === "steps") LAB.steps = part.steps; else LAB.table = { caption: part.caption, columns: part.columns, rows: part.rows };
    labDraw();
  }
  for (var kk in labBox) labBox[kk].addEventListener("input", function () { labPrint.textContent = labText(); });
  document.getElementById("labcopy").addEventListener("click", function () {
    var done = function () { labNote.textContent = "Report copied."; }, fail = function () { labNote.textContent = "Could not copy. Use Download lab report instead."; };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(labText()).then(done, fail); else fail();
  });
  document.getElementById("labsave").addEventListener("click", function () {
    var slug = labTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50) || "environment";
    var url = URL.createObjectURL(new Blob([labText()], { type: "text/plain;charset=utf-8" })), a = document.createElement("a");
    a.href = url; a.download = "lab-report-" + slug + ".txt"; a.click(); URL.revokeObjectURL(url);
    labNote.textContent = "Lab report saved.";
  });
  document.getElementById("labprintbtn").addEventListener("click", function () { labPrint.textContent = labText(); window.print(); });
"""


_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-src about: data:; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none';">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem; line-height: 1.5; }
  iframe { width: 100%; height: 70vh; min-height: 24rem; border: 1px solid #8884; border-radius: 12px; }
  section { margin-top: 1rem; padding: 1rem; border: 1px solid #8884; border-radius: 12px; font-size: 0.95rem; }
  [role=alert] { padding: 1rem; border-radius: 12px; background: #fde8e8; color: #7a1010; }
__LABCSS__
</style>
</head>
<body>
<h1>__TITLE__</h1>
<p id="state" role="status">Checking this file before it runs.</p>
<noscript><p role="alert">This Environment needs JavaScript to run. Turn it on and reload.</p></noscript>
<iframe id="frame" title="__TITLE__" sandbox="allow-scripts" hidden></iframe>
<section aria-label="Where this Environment comes from">
<p><strong>__LABEL__.</strong> Lane: __LANE__.</p>
<p>__PLAN__</p>
<p><strong>Source:</strong> __SOURCES__</p>
<p><strong>What was checked:</strong> __CHECKED__</p>
<p><strong>Limits:</strong> __LIMITS__</p>
<p>Environment __ID__, Kit __KIT__. This is a saved copy: it cannot be updated, and if the textbook or the Kit changes it may be out of date.</p>
</section>
__LABHTML__
<script>
(function () {
  var EXPECT = __EXPECT__;
  var PAYLOAD = __PAYLOAD__;
  var state = document.getElementById("state");
  var frame = document.getElementById("frame");
__LABJS__
  function fail(message) { state.setAttribute("role", "alert"); state.textContent = message; }
  function hex(buffer) { return Array.prototype.map.call(new Uint8Array(buffer), function (b) { return ("0" + b.toString(16)).slice(-2); }).join(""); }
  function sha(text) { return crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)).then(hex); }
  if (!window.crypto || !crypto.subtle) { fail("This browser cannot check the file's fingerprint, so it will not run the Environment. Open the file in a current browser."); return; }
  Promise.all([sha(PAYLOAD.html), sha(PAYLOAD.kit)]).then(function (got) {
    if (got[0] !== EXPECT.html || got[1] !== EXPECT.kit) { fail("This file does not match the fingerprint it was made with, so it was not run. Get a fresh copy."); return; }
    var at = PAYLOAD.html.indexOf(PAYLOAD.tag);
    if (at < 0) { fail("This file is damaged, so it was not run."); return; }
    frame.srcdoc = PAYLOAD.html.slice(0, at) + "<script>" + PAYLOAD.kit + "</" + "script>" + PAYLOAD.html.slice(at + PAYLOAD.tag.length);
    frame.hidden = false;
    labReset(PAYLOAD.title);
    state.textContent = "Fingerprint checked.";
  });
  window.addEventListener("message", function (event) {
    if (event.source !== frame.contentWindow) return;
    if (event.data && event.data.type === "synapse_violation") { frame.hidden = true; frame.removeAttribute("srcdoc"); labShut(); fail("The Environment tried to do something it must not, so it was closed."); }
    else if (event.data && event.data.type === "synapse_lab") labAccept(event.data);
  });
})();
</script>
</body>
</html>
"""


def standalone_page(block: EnvironmentBlock, kit_js: bytes) -> str:
    """The one-file export of `block` (already through the gate) with the Kit `kit_js` it was verified against."""
    tag = _kit_tag(block.kitVersion)
    if block.html.count(tag) != 1:
        raise ExportRefused("the page does not load the Kit from the expected tag exactly once")
    kit = kit_js.decode("utf-8")
    if re.search(r"</script", kit, re.IGNORECASE) or "<!--" in kit:
        raise ExportRefused("the Kit contains a sequence that would end its script element")
    if hashlib.sha256(block.html.encode("utf-8")).hexdigest() != block.htmlSha256:
        raise ExportRefused("the page does not match its recorded hash")

    esc = htmllib.escape
    sources = "; ".join(citation_text(c.source, c.page, c.verified, c.printedPage) for c in block.citations)
    c = block.checked
    checked = (
        f"{', '.join(c.layers)}; {c.controlsExercised} controls pressed, {c.gridPoints} positions swept, "
        f"{c.referenceCases} values compared with independent references"
    )
    values = {
        "__TITLE__": esc(block.title),
        "__LABEL__": esc(LABEL_TEXT[block.label]),
        "__LANE__": esc(LANE_TEXT[block.lane]),
        "__PLAN__": esc(block.planSummary),
        "__SOURCES__": esc(sources or "none stated"),
        "__CHECKED__": esc(checked),
        "__LIMITS__": esc(c.limits),
        "__ID__": esc(block.id),
        "__KIT__": esc(block.kitVersion),
        "__EXPECT__": _json_for_script({"html": block.htmlSha256, "kit": hashlib.sha256(kit_js).hexdigest()}),
        "__PAYLOAD__": _json_for_script({"html": block.html, "kit": kit, "tag": tag, "title": block.title}),
        "__LABCSS__": _LAB_CSS,
        "__LABHTML__": _LAB_HTML,
        "__LABJS__": _LAB_JS,
    }
    # One pass over the TEMPLATE: text that came from the block is never scanned again for placeholders.
    return re.sub(r"__[A-Z]+__", lambda m: values[m.group(0)], _SHELL)


# ── chapter packs (W6, D-49): several Environments in one offline file ─────────────────────────────────────────────────────────────────────────────

_PACK = """<!doctype html>
<html lang="en">
<head>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-src about: data:; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none';">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem; line-height: 1.5; }
  iframe { width: 100%; height: 70vh; min-height: 24rem; border: 1px solid #8884; border-radius: 12px; }
  section.prov { margin-top: 1rem; padding: 1rem; border: 1px solid #8884; border-radius: 12px; font-size: 0.95rem; }
  ul { list-style: none; padding: 0; display: grid; gap: .75rem; }
  li { border: 1px solid #8884; border-radius: 12px; padding: .75rem 1rem; }
  button { min-height: 44px; min-width: 44px; padding: 0 1rem; font: inherit; font-weight: 600; border-radius: 12px; border: 1px solid #8886; cursor: pointer; }
  button[disabled] { opacity: .6; cursor: not-allowed; }
  .meta { font-size: .9rem; opacity: .8; }
  [role=alert] { padding: 1rem; border-radius: 12px; background: #fde8e8; color: #7a1010; }
__LABCSS__
</style>
</head>
<body>
<h1>__TITLE__</h1>
<p id="state" role="status">Checking this file before anything runs.</p>
<noscript><p role="alert">This pack needs JavaScript to run. Turn it on and reload.</p></noscript>
<div id="list">
<ul>
__ITEMS__
</ul>
</div>
<div id="viewer" hidden>
<p><button type="button" id="back">Back to the list</button></p>
<iframe id="frame" title="Environment" sandbox="allow-scripts"></iframe>
__PROVENANCE__
__LABHTML__
</div>
<script>
(function () {
  var EXPECT = __EXPECT__;
  var PAYLOAD = __PAYLOAD__;
  var state = document.getElementById("state");
  var list = document.getElementById("list");
  var viewer = document.getElementById("viewer");
  var frame = document.getElementById("frame");
__LABJS__
  function fail(message) { state.setAttribute("role", "alert"); state.textContent = message; }
  function hex(buffer) { return Array.prototype.map.call(new Uint8Array(buffer), function (b) { return ("0" + b.toString(16)).slice(-2); }).join(""); }
  function sha(text) { return crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)).then(hex); }
  if (!window.crypto || !crypto.subtle) { fail("This browser cannot check the file's fingerprints, so it will not run any Environment. Open the file in a current browser."); return; }
  var ok = {};
  Promise.all([sha(PAYLOAD.kit)].concat(PAYLOAD.pages.map(function (p) { return sha(p.html); }))).then(function (got) {
    var kitOk = got[0] === EXPECT.kit;
    var good = 0;
    PAYLOAD.pages.forEach(function (p, i) {
      var fine = kitOk && got[i + 1] === EXPECT.pages[i] && p.html.indexOf(PAYLOAD.tag) >= 0;
      ok[p.id] = fine;
      var button = document.querySelector('button[data-open="' + p.id + '"]');
      if (fine) { good += 1; button.disabled = false; } else { button.textContent = "Not run: fingerprint does not match"; }
    });
    if (good === PAYLOAD.pages.length) state.textContent = "All " + good + " fingerprints checked.";
    else fail(good + " of " + PAYLOAD.pages.length + " Environments passed their fingerprint check. The others were not run. Get a fresh copy of this file.");
  });
  function show(id) {
    var p = PAYLOAD.pages.filter(function (x) { return x.id === id; })[0];
    if (!p || !ok[id]) return;
    var at = p.html.indexOf(PAYLOAD.tag);
    frame.title = p.title;
    frame.srcdoc = p.html.slice(0, at) + "<script>" + PAYLOAD.kit + "</" + "script>" + p.html.slice(at + PAYLOAD.tag.length);
    Array.prototype.forEach.call(document.querySelectorAll("section.prov"), function (s) { s.hidden = s.getAttribute("data-for") !== id; });
    labReset(p.title);
    list.hidden = true; viewer.hidden = false;
    document.getElementById("back").focus();
  }
  function home() {
    frame.removeAttribute("srcdoc"); labShut(); viewer.hidden = true; list.hidden = false;
    var b = document.querySelector("button[data-open]:not([disabled])"); if (b) b.focus();
  }
  Array.prototype.forEach.call(document.querySelectorAll("button[data-open]"), function (b) { b.addEventListener("click", function () { show(b.getAttribute("data-open")); }); });
  document.getElementById("back").addEventListener("click", home);
  window.addEventListener("message", function (event) {
    if (event.source !== frame.contentWindow) return;
    if (event.data && event.data.type === "synapse_violation") { home(); fail("An Environment tried to do something it must not, so it was closed."); }
    else if (event.data && event.data.type === "synapse_lab") labAccept(event.data);
  });
})();
</script>
</body>
</html>
"""


def chapter_pack(title: str, blocks: list[EnvironmentBlock], kit_js: bytes) -> str:
    """One offline file holding several Environments that were all verified against the same Kit. Each is checked against its own fingerprint (and the Kit against its) before
    the file lets it open, runs in its own `sandbox="allow-scripts"` frame, and keeps its provenance beside it. A block that did not come through the gate is the caller's
    bug; a block this function cannot place safely refuses the whole pack, so nothing half-built is handed out."""
    if not blocks:
        raise ExportRefused("a chapter pack needs at least one Environment")
    versions = {b.kitVersion for b in blocks}
    if len(versions) != 1:
        raise ExportRefused("the Environments were verified against different Kits, so they cannot share one")
    if len({b.id for b in blocks}) != len(blocks):
        raise ExportRefused("the same Environment appears twice")
    tag = _kit_tag(blocks[0].kitVersion)
    kit = kit_js.decode("utf-8")
    if re.search(r"</script", kit, re.IGNORECASE) or "<!--" in kit:
        raise ExportRefused("the Kit contains a sequence that would end its script element")
    esc = htmllib.escape
    items: list[str] = []
    provenance: list[str] = []
    for b in blocks:
        if b.html.count(tag) != 1:
            raise ExportRefused(f"'{b.title}' does not load the Kit from the expected tag exactly once")
        if hashlib.sha256(b.html.encode("utf-8")).hexdigest() != b.htmlSha256:
            raise ExportRefused(f"'{b.title}' does not match its recorded hash")
        sources = "; ".join(citation_text(c.source, c.page, c.verified, c.printedPage) for c in b.citations)
        c = b.checked
        checked = (
            f"{', '.join(c.layers)}; {c.controlsExercised} controls pressed, {c.gridPoints} positions swept, "
            f"{c.referenceCases} values compared with independent references"
        )
        items.append(
            f'<li><strong>{esc(b.title)}</strong><div class="meta">{esc(LABEL_TEXT[b.label])}. Source: {esc(sources or "none stated")}.</div>'
            f'<p class="meta">{esc(b.planSummary)}</p><button type="button" data-open="{esc(b.id)}" disabled>Open</button></li>'
        )
        provenance.append(
            f'<section class="prov" data-for="{esc(b.id)}" aria-label="Where this Environment comes from" hidden>'
            f"<p><strong>{esc(LABEL_TEXT[b.label])}.</strong> Lane: {esc(LANE_TEXT[b.lane])}.</p><p>{esc(b.planSummary)}</p>"
            f"<p><strong>Source:</strong> {esc(sources or 'none stated')}</p><p><strong>What was checked:</strong> {esc(checked)}</p>"
            f"<p><strong>Limits:</strong> {esc(c.limits)}</p>"
            f"<p>Environment {esc(b.id)}, Kit {esc(b.kitVersion)}. This is a saved copy: it cannot be updated, and if the textbook or the Kit changes it may be out of date.</p></section>"
        )
    values = {
        "__TITLE__": esc(title),
        "__ITEMS__": "\n".join(items),
        "__PROVENANCE__": "\n".join(provenance),
        "__LABCSS__": _LAB_CSS,
        "__LABHTML__": _LAB_HTML,
        "__LABJS__": _LAB_JS,
        "__EXPECT__": _json_for_script({"kit": hashlib.sha256(kit_js).hexdigest(), "pages": [b.htmlSha256 for b in blocks]}),
        "__PAYLOAD__": _json_for_script({"kit": kit, "tag": tag, "pages": [{"id": b.id, "title": b.title, "html": b.html} for b in blocks]}),
    }
    return re.sub(r"__[A-Z]+__", lambda m: values[m.group(0)], _PACK)
