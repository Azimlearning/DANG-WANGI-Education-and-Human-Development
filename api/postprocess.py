# Ported from Azimlearning/GenUI-Education, Synapse-V3/backend/postprocess.py (monorepo @ 835a2ce, v3 as of 2026-08). Read in
# full and adapted. Kept: single document, viewport and charset fixes, CSP injection that replaces any model-written CSP, size
# cap, and the rule order (the scan runs BEFORE our own CSP is injected). Changed: the CSP is path-scoped to /vendor/ on the
# configured origin, the scan lives in api/verify/scan.py, and v3's error banner is dropped (the Kit's environment() installs the
# error handlers). Not carried over: markdown-fence stripping and the CDN rewrite table (both are generation-lane concerns, P3).
"""Deterministic fixes and checks applied to an Environment's HTML before the render harness sees it.

The CSP must be the FIRST element the browser sees, or it governs nothing. Comments and other `<!` or `<?` constructs are removed or
refused first (a `<head>` inside a comment once made the injected CSP inert, found by kit-guardian B1), the CSP goes right after
the real `<head>` start tag found by an HTML tokenizer, and `csp_is_first` re-checks the result. The delivery gate runs the same check.

Each rule is a pure function `str -> str | PostprocessReject`. Order is load-bearing:
the L0 scan runs before the CSP and viewport tags are injected, so it never sees the origin literal we add ourselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from api.verify import scan
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


_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


class _Starts(HTMLParser):
    """Records start tags with their absolute end offset, using a real tokenizer (comments and script/style text are not tags)."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=False)
        self._line_starts = [0]
        for m in re.finditer("\n", html):
            self._line_starts.append(m.end())
        self.starts: list[tuple[str, int]] = []  # (tag, offset just past the start tag)
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        line, col = self.getpos()
        text = self.get_starttag_text() or ""
        self.starts.append((tag, self._line_starts[line - 1] + col + len(text)))


def strip_comments(html: str) -> str | PostprocessReject:
    """Remove HTML comments, and refuse any other markup declaration or processing instruction (`<![CDATA[`, `<?xml`, a stray
    `<!`) apart from one leading doctype. Browsers and tokenizers disagree about these, so none may remain."""
    stripped = _COMMENT.sub("", html)
    if "<!--" in stripped:
        return PostprocessReject("postprocess", "comment", "an unterminated HTML comment")
    body = re.sub(r"^\s*<!doctype\s+html[^>]*>", "", stripped, count=1, flags=re.IGNORECASE)
    if re.search(r"<[!?]", body):
        return PostprocessReject("postprocess", "markup_declaration", "a markup declaration or processing instruction")
    return stripped


def _open_tag_end(html: str, name: str) -> int | None:
    for tag, end in _Starts(html).starts:
        if tag == name:
            return end
    return None


def inject_csp(html: str, public_origin: str) -> str:
    """Remove any CSP the content wrote itself; ours is authoritative and goes right after the real <head> start tag."""
    html = scan.strip_csp_meta(html)
    tag = csp_tag(public_origin)
    head_end = _open_tag_end(html, "head")
    if head_end is not None:
        return html[:head_end] + "\n" + tag + html[head_end:]
    html_end = _open_tag_end(html, "html")
    if html_end is not None:
        return html[:html_end] + "\n<head>" + tag + "</head>" + html[html_end:]
    rest = re.sub(r"^\s*<!doctype\s+html[^>]*>", "", html, count=1, flags=re.IGNORECASE)
    return f"<!doctype html>\n<html><head>{tag}</head><body>{rest}</body></html>"


class _PrefixOnly(HTMLParser):
    def __init__(self, prefix: str):
        super().__init__(convert_charrefs=False)
        self.ok = True
        self.feed(prefix)

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag not in ("html", "head"):
            self.ok = False

    def handle_startendtag(self, tag: str, attrs) -> None:  # noqa: ANN001
        self.ok = False

    def handle_endtag(self, tag: str) -> None:
        self.ok = False

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.ok = False

    def handle_comment(self, data: str) -> None:
        self.ok = False

    def handle_pi(self, data: str) -> None:
        self.ok = False


def csp_is_first(html: str, public_origin: str) -> bool:
    """True when the document carries exactly one CSP, ours, and nothing but a doctype and the html and head start tags comes
    before it. Used by post-processing (after injection) and by the delivery gate (on the stored HTML)."""
    tag = csp_tag(public_origin)
    if html.count(tag) != 1 or html.lower().count("content-security-policy") != 1:
        return False
    prefix = html[: html.index(tag)]
    prefix = re.sub(r"^\s*<!doctype\s+html[^>]*>", "", prefix, count=1, flags=re.IGNORECASE)
    if re.search(r"<[!?]", prefix):  # a comment, declaration or processing instruction before the CSP
        return False
    if prefix.rfind("<") > prefix.rfind(">"):  # the prefix ends inside a tag
        return False
    parsed = _PrefixOnly(prefix)
    return parsed.ok and not parsed.rawdata.strip()  # nothing left buffered inside the tokenizer


def _inject_into_head(html: str, tag: str) -> str:
    head_end = _open_tag_end(html, "head")
    if head_end is not None:
        return html[:head_end] + "\n" + tag + html[head_end:]
    html_end = _open_tag_end(html, "html")
    if html_end is not None:
        return html[:html_end] + "\n<head>" + tag + "</head>" + html[html_end:]
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


def size_cap(html: str, max_bytes: int = MAX_BYTES) -> str | PostprocessReject:
    size = len(html.encode("utf-8"))
    if size > max_bytes:
        return PostprocessReject("postprocess", "size_cap", f"environment is {size} bytes (max {max_bytes})")
    return html


def run(html: str, *, public_origin: str, max_bytes: int = MAX_BYTES) -> str | PostprocessReject:
    """The ordered chain. Returns the processed HTML or the first refusal."""
    for rule in (strip_comments, enforce_single_document, scan_rule):
        result = rule(html)
        if isinstance(result, PostprocessReject):
            return result
        html = result
    html = ensure_charset(ensure_viewport(html))
    html = inject_csp(html, public_origin)
    if not csp_is_first(html, public_origin):
        return PostprocessReject("postprocess", "csp_position", "the CSP is not the first element of the document")
    return size_cap(html, max_bytes)
