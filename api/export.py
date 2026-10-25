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
<script>
(function () {
  var EXPECT = __EXPECT__;
  var PAYLOAD = __PAYLOAD__;
  var state = document.getElementById("state");
  var frame = document.getElementById("frame");
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
    state.textContent = "Fingerprint checked.";
  });
  window.addEventListener("message", function (event) {
    if (event.source !== frame.contentWindow) return;
    if (event.data && event.data.type === "synapse_violation") { frame.hidden = true; frame.removeAttribute("srcdoc"); fail("The Environment tried to do something it must not, so it was closed."); }
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
    sources = "; ".join(citation_text(c.source, c.page, c.verified) for c in block.citations)
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
        "__PAYLOAD__": _json_for_script({"html": block.html, "kit": kit, "tag": tag}),
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
</div>
<script>
(function () {
  var EXPECT = __EXPECT__;
  var PAYLOAD = __PAYLOAD__;
  var state = document.getElementById("state");
  var list = document.getElementById("list");
  var viewer = document.getElementById("viewer");
  var frame = document.getElementById("frame");
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
    list.hidden = true; viewer.hidden = false;
    document.getElementById("back").focus();
  }
  function home() {
    frame.removeAttribute("srcdoc"); viewer.hidden = true; list.hidden = false;
    var b = document.querySelector("button[data-open]:not([disabled])"); if (b) b.focus();
  }
  Array.prototype.forEach.call(document.querySelectorAll("button[data-open]"), function (b) { b.addEventListener("click", function () { show(b.getAttribute("data-open")); }); });
  document.getElementById("back").addEventListener("click", home);
  window.addEventListener("message", function (event) {
    if (event.source !== frame.contentWindow) return;
    if (event.data && event.data.type === "synapse_violation") { home(); fail("An Environment tried to do something it must not, so it was closed."); }
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
        sources = "; ".join(citation_text(c.source, c.page, c.verified) for c in b.citations)
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
        "__EXPECT__": _json_for_script({"kit": hashlib.sha256(kit_js).hexdigest(), "pages": [b.htmlSha256 for b in blocks]}),
        "__PAYLOAD__": _json_for_script({"kit": kit, "tag": tag, "pages": [{"id": b.id, "title": b.title, "html": b.html} for b in blocks]}),
    }
    return re.sub(r"__[A-Z]+__", lambda m: values[m.group(0)], _PACK)
