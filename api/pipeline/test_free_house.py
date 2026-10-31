"""W20 (D-80): a model-written lab comes back in labelled sections and is assembled into the house frame. The parse refuses an incomplete or malformed reply with a
reason the model is told on its retry; the assembled page passes the same checks as any Free page, in a real browser."""

from __future__ import annotations

from pathlib import Path

import pytest

from api import postprocess
from api.kit import latest_version
from api.pipeline import free, free_house
from api.pipeline.grounding import UNCHECKED_CITATION
from api.verify.mint import verify_environment

SECTIONS = (Path(__file__).resolve().parents[2] / "data" / "fixtures" / "envs" / "free-pressure-sections.txt").read_text(encoding="utf-8")
ORIGIN = "http://localhost:3000"


def test_a_sectioned_reply_becomes_a_house_page_with_every_part_of_a_lab() -> None:
    page = free.read_reply(SECTIONS)
    assert isinstance(page, free.Page) and page.title == "Pressure and depth"
    for part in ("Try this:", "Key idea", "Predict first", "Check your prediction", "Steps", "Keyboard controls", "Need a hint?", "Why it happens", 'id="found"'):
        assert part in page.html, part
    assert 'data-synapse-control="depth"' in page.html and 'aria-valuetext="2 m"' in page.html and 'for="depth"' in page.html
    assert 'data-synapse-readout="pressure"' in page.html and 'aria-labelledby="pressure-name"' in page.html
    assert "synapse_theme" in page.html  # it follows the app's light or dark switch, like a Kit lab
    assert page.html.count("<script>") == 1


def test_model_text_is_escaped_and_only_the_code_sections_are_taken_as_markup() -> None:
    page = free.read_reply(SECTIONS.replace("Pressure and depth", "Pressure <b>and</b> depth", 1))
    assert isinstance(page, free.Page)
    assert "Pressure &lt;b&gt;and&lt;/b&gt; depth" in page.html and "<b>and</b>" not in page.html


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        (lambda s: s.replace("@@END\n", ""), "cut off"),
        (lambda s: s.replace("@@SCRIPT", "@@CODE"), "missing these sections: @@SCRIPT"),
        (lambda s: s.replace("depth | Depth | 0 | 10 | 0.5 | 2 | m", "depth | Depth | 0 | 10"), "is not 'id | label"),
        (lambda s: s.replace("depth | Depth | 0 | 10 | 0.5 | 2 | m", "depth | Depth | 0 | 10 | 0.5 | 20 | m"), "start inside the range"),
        (lambda s: s.replace("pressure | Pressure", "depth | Pressure"), "its own id"),
        (lambda s: s.replace("<svg", "<div").replace("</svg>", "</div>"), "<svg>"),
        (lambda s: s.replace("@@SCRIPT\n", "@@SCRIPT\n<script>\n"), "without tags"),
    ],
    ids=["cut-off", "no-script", "short-control", "start-outside", "duplicate-id", "no-svg", "script-tag"],
)
def test_an_incomplete_or_malformed_reply_is_refused_with_a_reason_for_the_retry(change, fragment: str) -> None:  # noqa: ANN001
    reason = free.read_reply(change(SECTIONS))
    assert isinstance(reason, str) and fragment in reason


def test_a_whole_document_reply_is_still_read_as_before() -> None:
    page = free.read_reply("<!doctype html><html lang=\"en\"><head><title>T</title></head><body></body></html>")
    assert isinstance(page, free.Page) and page.title == "T"


def test_the_house_page_passes_the_free_checks_in_a_real_browser(kit_dist: Path) -> None:
    page = free.read_reply(SECTIONS)
    assert isinstance(page, free.Page)
    assert not isinstance(postprocess.run(page.html, public_origin=ORIGIN), postprocess.PostprocessReject)
    env = verify_environment(
        slug="free_house_test",
        title=page.title,
        raw_html=page.html,
        lane="free",
        label="model-checked",
        kit_version=latest_version(kit_dist),
        citations=[UNCHECKED_CITATION],
        plan_summary="A page written by a model in the house frame.",
        public_origin=ORIGIN,
        kit_dist=kit_dist,
        interaction_seconds=1.0,
        plan_models=None,
    )
    assert env.lane == "free" and env.checked.controls_exercised == 1


def test_house_css_has_no_generated_content_pseudo_elements_or_counters() -> None:
    import re

    assert not re.search(r"content\s*:\s*[\"'`]", free_house.HOUSE_CSS)
    assert "::" not in free_house.HOUSE_CSS and "counter" not in free_house.HOUSE_CSS
