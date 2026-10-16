"""Hard constraint 10 in a real browser, for everything a student can operate or must read (not only the declared controls):
a name, a 44 px target, keyboard reach, a text equivalent for every picture, no motion under prefers-reduced-motion, a document language."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.verify import render

ORIGIN = "http://localhost:3000"


def audit(body: str, style: str = "", lang: str = "en") -> list[str]:
    page = (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><style>{style}</style></head><body>{body}'
        '<script>parent.postMessage({type:"synapse_ready"},"*")</script></body></html>'
    )
    report = render.render_check(
        page,
        kit_dist=Path(__file__).resolve().parents[2] / "packages" / "kit" / "dist",
        public_origin=ORIGIN,
        interaction_seconds=0.2,
        kit_lane=False,
        require_controls=False,
    )
    assert report.ready
    return report.a11y_problems


GOOD = '<button style="width:60px;height:50px">Show hint</button><svg width="30" height="30" role="img" aria-label="Graph of speed against time"></svg>'


def test_a_compliant_page_has_no_problems() -> None:
    assert audit(GOOD) == []


@pytest.mark.parametrize(
    ("body", "style", "lang", "expected"),
    [
        ('<button style="width:60px;height:50px"></button>', "", "en", "no accessible name"),
        ('<button style="width:20px;height:20px">Hint</button>', "", "en", "under the 44 px touch target"),
        (
            '<a href="#x" style="display:block;width:60px;height:50px" tabindex="-1">Link</a>',
            "",
            "en",
            "cannot be reached with the keyboard",
        ),
        ('<canvas width="50" height="50"></canvas>', "", "en", "canvas has no text equivalent"),
        ('<svg width="30" height="30"></svg>', "", "en", "svg has no text equivalent"),
        ('<div class="a">x</div>', "@keyframes s{to{opacity:.5}} .a{animation:s 5s infinite}", "en", "reduced motion"),
        ("<p>text</p>", "", "", "no lang attribute"),
    ],
)
def test_each_failure_is_caught(body: str, style: str, lang: str, expected: str) -> None:
    assert any(expected in p for p in audit(body, style, lang)), expected


def test_a_picture_hidden_from_assistive_technology_needs_no_label_and_a_hidden_element_is_ignored() -> None:
    assert audit('<svg width="30" height="30" aria-hidden="true"></svg><button hidden>x</button>') == []


def test_a_radio_inside_a_large_enough_label_passes() -> None:
    body = '<label style="display:block;min-width:60px;min-height:50px"><input type="radio" name="q"> It halves</label>'
    assert audit(body) == []
