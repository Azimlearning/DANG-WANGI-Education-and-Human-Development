"""CSS counters and `@counter-style` can put a number on the screen with no text node (D-37). Named at L0 for Kit pages and for Free pages as well as in the Kit's own
audit, because a stylesheet check that names `counter-reset` but not `@counter-style` leaves a way round it (kit-guardian, W3 review)."""

from __future__ import annotations

import pytest

from api.verify import scan

COUNTER_CSS = [
    "ol{counter-reset:list-item 8}",
    "li{counter-increment:n 41}",
    "body{counter-set:n 3}",
    '@counter-style fx{system:fixed;symbols:"9.81"} ol{list-style-type:fx}',
]


@pytest.mark.parametrize("css", COUNTER_CSS)
def test_a_kit_page_with_a_counter_or_counter_style_is_refused_at_l0(css: str) -> None:
    hit = scan.kit_lane_scan(f"<html><head><style>{css}</style></head><body><ol><li>x</li></ol></body></html>")
    assert hit is not None and hit.rule == "kit_lane" and "CSS counters" in hit.reason


@pytest.mark.parametrize("css", COUNTER_CSS)
def test_a_free_page_with_a_counter_or_counter_style_is_refused_at_l0(css: str) -> None:
    hit = scan.free_lane_scan(f"<html><head><style>{css}</style></head><body><ol><li>x</li></ol></body></html>")
    assert hit is not None and hit.rule == "free_lane_scan" and "CSS counters" in hit.reason


def test_an_ordinary_stylesheet_passes_both() -> None:
    html = "<html><head><style>p{color:#333;margin:0}</style></head><body><p>hi</p></body></html>"
    assert scan.kit_lane_scan(html) is None and scan.free_lane_scan(html) is None
