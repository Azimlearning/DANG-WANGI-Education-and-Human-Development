# Ported from Azimlearning/GenUI-Education, Synapse-V3/backend/postprocess.py (monorepo @ 835a2ce, v3 as of 2026-08). Read in
# full and adapted. Kept: single document, viewport and charset fixes, CSP injection that replaces any model-written CSP, size
# cap, and the rule order (the scan runs BEFORE our own CSP is injected). Changed: the CSP is path-scoped to /vendor/ on the
# configured origin, the scan lives in api/verify/scan.py, and v3's error banner is dropped (the Kit's environment() installs the
# error handlers). Not carried over: markdown-fence stripping and the CDN rewrite table (both are generation-lane concerns, P3).
"""Deterministic fixes and checks applied to an Environment's HTML before the render harness sees it.

Each rule is a pure function `str -> str | PostprocessReject`. Order is load-bearing:
the L0 scan runs before the CSP and viewport tags are injected, so it never sees the origin literal we add ourselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from api.verify import scan as l0

MAX_BYTES = 200_000


@dataclass(frozen=True)
class PostprocessReject:
    stage: str
    rule: str
    reason: str


def normalise_origin(public_origin: str) -> str:
    """`http://localhost:3000/` to `http://localhost:3000`. Anything with a path, query or no scheme is not an origin."""
    origin = public_origin.rstrip("/")
    if not re.fullmatch(r"https?://[A-Za-z0-9.-]+(:\d+)?", origin):
        raise ValueError(f"PUBLIC_ORIGIN must be an origin such as http://localhost:3000, got {public_origin!r}")
    return origin


def build_csp(public_origin: str) -> str:
    """The artifact CSP. It names the configured origin explicitly because an opaque-origin srcdoc makes 'self' match nothing
    (hard constraint 2). Scripts and fonts are scoped to /vendor/ on that origin; nothing may connect anywhere."""
    origin = normalise_origin(public_origin)
    return (
        "default-src 'none'; "
        f"script-src 'unsafe-inline' {origin}/vendor/; "
        "style-src 'unsafe-inline'; "
        "img-src data:; "
        f"font-src {origin}/vendor/ data:; "
        "connect-src 'none'; frame-src 'none'; object-src 'none'; "
        "base-uri 'none'; form-action 'none';"
    )


def csp_tag(public_origin: str) -> str:
    return f'<meta http-equiv="Content-Security-Policy" content="{build_csp(public_origin)}">'


_CSP_META = re.compile(r"<meta\b[^>]*http-equiv\s*=\s*[\"']Content-Security-Policy[\"'][^>]*>", re.IGNORECASE)


def _inject_into_head(html: str, tag: str) -> str:
    match = re.search(r"<head\b[^>]*>", html, flags=re.IGNORECASE)
    if match:
        return html[: match.end()] + "\n" + tag + html[match.end() :]
    match = re.search(r"<html\b[^>]*>", html, flags=re.IGNORECASE)
    if match:
        return html[: match.end()] + "\n<head>" + tag + "</head>" + html[match.end() :]
    return tag + "\n" + html


def enforce_single_document(html: str) -> str | PostprocessReject:
    """Fixes a missing doctype. Refuses more than one <html> element."""
    if len(re.findall(r"<html\b", html, flags=re.IGNORECASE)) > 1:
        return PostprocessReject("postprocess", "single_document", "more than one <html> element")
    if not re.match(r"\s*<!doctype\s+html", html, flags=re.IGNORECASE):
        html = "<!doctype html>\n" + html
    return html


def scan_rule(html: str) -> str | PostprocessReject:
    hit = l0.scan(html)
    if hit is not None:
        return PostprocessReject("scan", hit.rule, hit.reason)
    return html


def ensure_viewport(html: str) -> str:
    if re.search(r"<meta\b[^>]*name\s*=\s*[\"']viewport[\"']", html, flags=re.IGNORECASE):
        return html
    return _inject_into_head(html, '<meta name="viewport" content="width=device-width, initial-scale=1">')


def ensure_charset(html: str) -> str:
    if re.search(r"<meta\b[^>]*charset", html, flags=re.IGNORECASE):
        return html
    return _inject_into_head(html, '<meta charset="utf-8">')


def inject_csp(html: str, public_origin: str) -> str:
    """Remove any CSP the content wrote itself; ours is authoritative and lands first in <head>."""
    html = _CSP_META.sub("", html)
    return _inject_into_head(html, csp_tag(public_origin))


def size_cap(html: str, max_bytes: int = MAX_BYTES) -> str | PostprocessReject:
    size = len(html.encode("utf-8"))
    if size > max_bytes:
        return PostprocessReject("postprocess", "size_cap", f"environment is {size} bytes (max {max_bytes})")
    return html


def run(html: str, *, public_origin: str, max_bytes: int = MAX_BYTES) -> str | PostprocessReject:
    """The ordered chain. Returns the processed HTML or the first refusal."""
    for rule in (enforce_single_document, scan_rule):
        result = rule(html)
        if isinstance(result, PostprocessReject):
            return result
        html = result
    html = ensure_charset(ensure_viewport(html))
    html = inject_csp(html, public_origin)
    return size_cap(html, max_bytes)
