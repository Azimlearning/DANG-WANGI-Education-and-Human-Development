# Ported from Azimlearning/GenUI-Education, Synapse-V3/backend/postprocess.py (monorepo @ 835a2ce, v3 as of 2026-08): the
# forbidden-API deny list and the "remove our own sanctioned text before scanning" ordering rule. Read in full and adapted:
# v4 allows exactly one script source family (the Kit at /vendor/kit/<semver>/), so the v3 CDN rewrite table is not carried over
# (a CDN URL is simply refused; vendored libraries return with P3).
"""L0: the deterministic scan. A pure function of the HTML text; no browser, no Kit contract.

A hit is a refusal, never an auto-strip: stripping produces silently broken environments (v3 SECURITY.md section 3). This is
the independent second layer. The semantic layers (L1, L3, L6) arrive in P1 and cannot be replaced by it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# The CSP meta that api/postprocess.py injects names the public origin by design, so it is removed before scanning: the scan
# then covers exactly the generated content. ONE regex, shared with postprocess (strip_csp_meta), so what is scanned is exactly
# what is minted (a different strip in each place let a CSP-shaped fragment hide a deny-list word at mint time).
_CSP_META = re.compile(r"<meta\b[^>]*http-equiv\s*=\s*[\"']Content-Security-Policy[\"'][^>]*>", re.IGNORECASE)

# A script may load only from the Kit, versioned. Anything else is refused (hard constraint 2: no runtime CDN).
KIT_SCRIPT_SRC = re.compile(r"^/vendor/kit/\d+\.\d+\.\d+/[A-Za-z0-9_.-]+\.js$")

# (pattern, label). The label is what the refusal names.
FORBIDDEN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bfetch\s*\("), "fetch"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\bWebSocket\b"), "WebSocket"),
    (re.compile(r"\bEventSource\b"), "EventSource"),
    (re.compile(r"\bsendBeacon\b"), "navigator.sendBeacon"),
    (re.compile(r"\bimportScripts\b"), "importScripts"),
    (re.compile(r"\bimport\s*\("), "dynamic import()"),
    (re.compile(r"^\s*import\s+", re.MULTILINE), "ES module import"),
    (re.compile(r"^\s*export\s+", re.MULTILINE), "ES module export"),
    (re.compile(r"\beval\s*\("), "eval"),
    (re.compile(r"\bnew\s+Function\b"), "new Function"),
    (re.compile(r"document\s*\.\s*cookie"), "document.cookie"),
    (re.compile(r"\blocalStorage\b"), "localStorage"),
    (re.compile(r"\bsessionStorage\b"), "sessionStorage"),
    (re.compile(r"\bindexedDB\b"), "indexedDB"),
    (re.compile(r"window\s*\.\s*open\s*\("), "window.open"),
    (re.compile(r"window\s*\.\s*parent\b"), "window.parent"),
    (re.compile(r"window\s*\.\s*top\b"), "window.top"),
    (re.compile(r"location\s*\.\s*(assign|replace)\s*\("), "location navigation"),
    (re.compile(r"location\s*\.\s*href\s*="), "location.href write"),
    # Navigation. CSP does not govern it and sandbox="allow-scripts" still lets a frame navigate itself. A bare `location = x`
    # was missed by the first version of this list (found by kit-guardian, B2).
    (re.compile(r"(?<![\w$])location\s*=(?!=)"), "location assignment"),
    (
        re.compile(
            r"(?<![\w$])location\s*\.\s*(href|assign|replace|reload|pathname|search|hash|host|hostname|protocol|port|origin)\b"
        ),
        "location navigation",
    ),
    (re.compile(r"\b(?:window|self|top|parent|globalThis|document)\s*\.\s*location\b"), "window.location"),
    (re.compile(r"<meta\b[^>]*http-equiv\s*=\s*[\"']?refresh", re.IGNORECASE), "meta refresh"),
    (re.compile(r"javascript\s*:", re.IGNORECASE), "javascript: URL"),
    (re.compile(r"data\s*:\s*text/html", re.IGNORECASE), "data:text/html URL"),
    (
        re.compile(r"<\s*(form|iframe|object|embed|base|portal|frame|frameset)\b", re.IGNORECASE),
        "embedding or form element",
    ),
    (re.compile(r"\bsrcdoc\b", re.IGNORECASE), "srcdoc"),
    (re.compile(r"document\s*\.\s*write"), "document.write"),
    (re.compile(r"\bpostMessage\b"), "postMessage"),
    (re.compile(r"\b(?:self|globalThis)\s*\.\s*(?:parent|top)\b"), "self.parent or self.top"),
    (re.compile(r"\bFunction\s*\("), "Function constructor"),
    (re.compile(r"\b(?:setTimeout|setInterval)\s*\(\s*[\"'`]"), "string timer (eval)"),
    (re.compile(r"(?<![\w$.])open\s*\("), "open"),
    (re.compile(r"@import\b", re.IGNORECASE), "CSS @import"),
    (re.compile(r"\bNotification\b"), "Notification"),
    (re.compile(r"\bgeolocation\b"), "geolocation"),
    (re.compile(r"\bgetUserMedia\b"), "getUserMedia"),
    (re.compile(r"\bserviceWorker\b"), "serviceWorker"),
    (re.compile(r"\bSharedWorker\b"), "SharedWorker"),
    (re.compile(r"\bnew\s+Worker\s*\("), "Worker"),
    (re.compile(r"https?://", re.IGNORECASE), "absolute URL"),
    (re.compile(r"(?:src|href)\s*=\s*[\"']//"), "protocol-relative URL"),
    (re.compile(r"url\(\s*[\"']?//"), "protocol-relative URL in CSS"),
]

_SCRIPT_SRC = re.compile(r"<script\b[^>]*\bsrc\s*=\s*[\"']([^\"']*)[\"'][^>]*>", re.IGNORECASE)
_LINK_HREF = re.compile(r"<link\b[^>]*\bhref\s*=\s*[\"']([^\"']*)[\"'][^>]*>", re.IGNORECASE)


@dataclass(frozen=True)
class ScanReject:
    rule: str
    reason: str


def strip_csp_meta(html: str) -> str:
    return _CSP_META.sub("", html)


strip_injected_csp = strip_csp_meta


def forbidden_api_scan(html: str) -> ScanReject | None:
    """The deny list. Returns a reject naming every API hit, or None."""
    scannable = strip_injected_csp(html)
    hits = [label for pattern, label in FORBIDDEN_PATTERNS if pattern.search(scannable)]
    if hits:
        return ScanReject("forbidden_api", "forbidden API(s): " + ", ".join(hits))
    return None


def script_source_scan(html: str) -> ScanReject | None:
    """Every <script src> must be a versioned Kit file; every <link href> is refused (no external stylesheet is allowed)."""
    scannable = strip_injected_csp(html)
    for match in _SCRIPT_SRC.finditer(scannable):
        src = match.group(1)
        if not KIT_SCRIPT_SRC.match(src):
            return ScanReject("script_source", f"script source is not a versioned Kit file: {src}")
    for match in _LINK_HREF.finditer(scannable):
        return ScanReject("link_href", f"external stylesheet or link is not allowed: {match.group(1)}")
    return None


def scan(html: str) -> ScanReject | None:
    """L0 in full: the forbidden-API deny list, then the script-source allow list. The first hit wins."""
    return forbidden_api_scan(html) or script_source_scan(html)


# ── rules that apply to Kit lanes (Instantiate and Compose) only ───────────────────────────────────────────────────────
# In a Kit lane every number on the page must come from the Kit, so the ways a page could draw or inject a number the DOM text scan
# cannot see are closed: canvas drawing, images (including data URIs) and CSS generated content. The Free lane (no Kit, `model-checked`
# at most) is exempt. This is defence in depth; the L1 audit is the real check.
KIT_LANE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"<\s*canvas\b", re.IGNORECASE), "canvas"),
    (re.compile(r"\bgetContext\b"), "canvas context"),
    (re.compile(r"\b(?:fillText|strokeText)\b"), "canvas text"),
    (re.compile(r"<\s*img\b", re.IGNORECASE), "image"),
    (re.compile(r"data\s*:\s*image", re.IGNORECASE), "image data URL"),
    (re.compile(r"\bcontent\s*:\s*[\"'`]", re.IGNORECASE), "CSS generated content"),
    (re.compile(r"::?(?:before|after)\b", re.IGNORECASE), "CSS pseudo-element"),
    (re.compile(r"<\s*(?:video|audio|source|track|svg\s+[^>]*\bimage)\b", re.IGNORECASE), "media element"),
    (re.compile(r"\bFontFace\b|@font-face", re.IGNORECASE), "custom font"),
    (re.compile(r"\burl\s*\(|\bimage-set\s*\(|@import", re.IGNORECASE), "CSS image or import"),
    (re.compile(r"\battachShadow\b"), "shadow DOM"),
    (re.compile(r"\bcustomElements\b"), "custom elements"),
]

_SCRIPT_TAG = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
_SRC = re.compile(r"\bsrc\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)


def kit_lane_scan(html: str) -> ScanReject | None:
    scannable = strip_csp_meta(html)
    hits = [label for pattern, label in KIT_LANE_PATTERNS if pattern.search(scannable)]
    if hits:
        return ScanReject("kit_lane", "not allowed in a Kit-lane Environment: " + ", ".join(hits))
    return None


def kit_first_script(html: str, kit_version: str) -> ScanReject | None:
    """The Kit must be the FIRST script and appear exactly once, so no page script runs before it can capture the DOM functions it
    relies on (a later script could patch them) and so `window.Synapse` cannot be pre-defined by the page."""
    expected = f"/vendor/kit/{kit_version}/core.js"
    tags = _SCRIPT_TAG.findall(strip_csp_meta(html))
    if not tags:
        return ScanReject("kit_first", "a Kit-lane Environment must load the Kit")
    first = _SRC.search(tags[0])
    if not first or first.group(1) != expected:
        return ScanReject("kit_first", f"the first script must be the Kit ({expected})")
    if sum(1 for t in tags if (m := _SRC.search(t)) and m.group(1) == expected) != 1:
        return ScanReject("kit_first", "the Kit must be loaded exactly once")
    return None
