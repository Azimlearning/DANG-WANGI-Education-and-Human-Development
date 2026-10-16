"""L0 in isolation: a pure function of the HTML text."""

import pytest

from api.verify import scan

GOOD = '<script src="/vendor/kit/0.0.1/core.js"></script><script>Synapse.environment({title:"t",note:"n"})</script>'


def test_clean_kit_document_passes() -> None:
    assert scan.scan(GOOD) is None


@pytest.mark.parametrize(
    ("snippet", "label"),
    [
        ("fetch('/x')", "fetch"),
        ("new XMLHttpRequest()", "XMLHttpRequest"),
        ("new WebSocket('x')", "WebSocket"),
        ("navigator.sendBeacon('x')", "navigator.sendBeacon"),
        ("eval('1')", "eval"),
        ("new Function('1')", "new Function"),
        ("document.cookie", "document.cookie"),
        ("localStorage.x", "localStorage"),
        ("window.parent.postMessage(1,'*')", "window.parent"),
        ("window.top.x", "window.top"),
        ("location.href = 'x'", "location.href write"),
        ("x = 'https://evil.example'", "absolute URL"),
        ("import('x')", "dynamic import()"),
    ],
)
def test_each_forbidden_api_is_named(snippet: str, label: str) -> None:
    hit = scan.scan(f"<script>{snippet}</script>")
    assert hit is not None
    assert label in hit.reason


def test_a_cdn_script_is_refused() -> None:
    hit = scan.scan('<script src="/vendor/p5.min.js"></script>')
    assert hit is not None
    assert hit.rule == "script_source"


def test_a_script_from_another_kit_path_is_refused() -> None:
    assert scan.scan('<script src="/vendor/kit/latest/core.js"></script>') is not None
    assert scan.scan('<script src="/vendor/kit/0.0.1/../../x.js"></script>') is not None


def test_an_external_stylesheet_is_refused() -> None:
    hit = scan.scan('<link rel="stylesheet" href="/vendor/x.css">')
    assert hit is not None
    assert hit.rule == "link_href"


def test_our_own_csp_origin_is_not_scanned() -> None:
    html = '<meta http-equiv="Content-Security-Policy" content="script-src http://localhost:3000/vendor/;">' + GOOD
    assert scan.scan(html) is None
