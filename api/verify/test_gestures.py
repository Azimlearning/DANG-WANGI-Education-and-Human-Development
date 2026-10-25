"""W4 stage 2: the harness really operates a stopcock and an eye (L2). The titration bench is minted; a page whose stopcock or eye does nothing is refused (`valve_dead`, `eye_dead`); a
scene drawn from the wrong model, at the wrong scale, or redrawn, hidden or relabelled by the page is refused. Real Chromium, real mouse, keyboard and touch."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from api.verify.conftest import fixture_html, mint
from api.verify.mint import VerificationFailed, VerifiedEnvironment

NAME = "reference-titration.html"
READY = "Synapse.bridge.ready();"


def variant(edit: Callable[[str], str]) -> str:
    return edit(fixture_html(NAME))


def before_ready(js: str) -> Callable[[str], str]:
    return lambda html: html.replace(READY, js + "\n  " + READY, 1)


def refused(kit_dist: Path, html: str) -> VerificationFailed:
    with pytest.raises(VerificationFailed) as err:
        mint(kit_dist, NAME, raw_html=html)
    return err.value


@pytest.fixture(scope="module")
def minted(kit_dist: Path) -> VerifiedEnvironment:
    return mint(kit_dist, NAME)


def test_the_titration_bench_is_minted_with_its_stopcock_held_and_its_eye_moved(minted: VerifiedEnvironment) -> None:
    assert minted.checked.layers[:3] == ("postprocess", "scan", "render")
    assert "provenance" in minted.checked.layers and "grid" in minted.checked.layers and "reference" in minted.checked.layers
    assert minted.checked.controls_exercised == 1
    assert ("chemistry.titration_endpoint_volume", (("acid_coeff", 1.0), ("base_coeff", 1.0), ("ma", 0.1))) in minted.checked.models
    assert "Synapse.valve" in minted.html and "Synapse.titrationScene" in minted.html


@pytest.mark.parametrize(
    ("js", "needle"),
    [
        ('document.addEventListener("pointerdown", function (e) { e.stopImmediatePropagation(); }, true);', "stopcock"),
        ('document.addEventListener("click", function (e) { e.stopImmediatePropagation(); }, true);', "stopcock"),
        ('["keydown", "keyup"].forEach(function (n) { document.addEventListener(n, function (e) { e.preventDefault(); e.stopImmediatePropagation(); }, true); });', "stopcock"),
        ('document.addEventListener("pointerdown", function (e) { if (e.pointerType === "touch") e.stopImmediatePropagation(); }, true);', "finger"),
    ],
    ids=["pointer-swallowed", "click-swallowed", "keys-swallowed", "finger-swallowed"],
)
def test_a_stopcock_the_page_made_dead_is_refused(kit_dist: Path, js: str, needle: str) -> None:
    e = refused(kit_dist, variant(before_ready(js)))
    assert (e.stage, e.rule) == ("render", "valve_dead")
    assert needle in e.reason


def test_a_stopcock_that_keeps_running_after_the_pointer_is_lifted_is_refused(kit_dist: Path) -> None:
    js = 'document.addEventListener("pointerup", function (e) { e.stopImmediatePropagation(); }, true); document.addEventListener("pointercancel", function (e) { e.stopImmediatePropagation(); }, true);'
    e = refused(kit_dist, variant(before_ready(js)))
    assert (e.stage, e.rule) == ("render", "valve_dead")


@pytest.mark.parametrize(
    "js",
    [
        'document.addEventListener("pointerdown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) e.stopImmediatePropagation(); }, true);',
        'document.addEventListener("keydown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);',
    ],
    ids=["eye-pointer-swallowed", "eye-keys-swallowed"],
)
def test_an_eye_the_page_made_dead_is_refused(kit_dist: Path, js: str) -> None:
    e = refused(kit_dist, variant(before_ready(js)))
    assert (e.stage, e.rule) == ("render", "eye_dead")


def test_a_stopcock_or_eye_the_page_made_itself_is_refused(kit_dist: Path) -> None:
    fake = '<button data-synapse-action="valve" data-synapse-valve="vb">Stopcock</button>'
    assert refused(kit_dist, variant(lambda h: h.replace("</body>", fake + "\n</body>", 1))).stage == "render"
    fake_eye = '<button data-synapse-action="eye" data-synapse-eye>Eye</button>'
    assert refused(kit_dist, variant(lambda h: h.replace("</body>", fake_eye + "\n</body>", 1))).stage == "render"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("added: c_vb", "added: Synapse.observable(10)"),
        ("added: c_vb", "added: m_endpoint"),
        ("endpoint: m_endpoint", "endpoint: c_vb"),
        ("endpoint: m_endpoint", "endpoint: Synapse.observable(20)"),
        ("endpoint: m_endpoint", "endpoint: m_alkali"),
    ],
    ids=["free-added", "model-as-added", "control-as-endpoint", "free-endpoint", "other-model-as-endpoint"],
)
def test_a_scene_bound_to_anything_but_a_cm3_control_and_the_endpoint_model_is_refused(kit_dist: Path, old: str, new: str) -> None:
    assert refused(kit_dist, variant(lambda h: h.replace(old, new, 1))).stage == "render"


def test_a_burette_drawn_to_the_wrong_capacity_is_refused(kit_dist: Path) -> None:
    for full in ("30", "1000"):
        e = refused(kit_dist, variant(lambda h, f=full: h.replace("full: 50.0", f"full: {f}", 1)))
        assert e.stage == "render"


@pytest.mark.parametrize(
    "tamper",
    [
        'document.querySelector(".syn-titration rect[fill=\\"var(--syn-liquid)\\"]").setAttribute("y", "40");',
        'document.querySelector(".syn-titration path").setAttribute("fill", "var(--syn-card)");',
        'document.querySelector(".syn-titration").setAttribute("aria-label", "A full burette above a pink flask.");',
        'document.querySelector("[data-synapse-eye]").style.top = "2%";',
        'document.querySelector(".syn-titration").style.visibility = "hidden";',
        'document.querySelector("[data-synapse-meniscus]").setAttribute("y1", "20");',
    ],
    ids=["liquid-redrawn", "flask-colour-forced", "relabelled", "eye-moved", "hidden", "meniscus-moved"],
)
def test_a_burette_scene_a_page_redraws_recolours_relabels_or_hides_is_refused(kit_dist: Path, tamper: str) -> None:
    e = refused(kit_dist, variant(before_ready(f"setInterval(function () {{ {tamper} }}, 20);")))
    assert e.stage == "render"


@pytest.mark.parametrize(
    "rule",
    [
        ".syn-titration{transform:scale(1,.3)}",
        ".syn-titr-frame{opacity:.02}",
        ".syn-eye{margin-top:200px}",
        ".syn-valve{max-width:20px;min-width:0;padding:0;overflow:hidden}",
    ],
    ids=["squashed", "faded", "eye-shifted-by-css", "stopcock-shrunk"],
)
def test_style_rules_that_squash_fade_or_shift_the_bench_are_refused(kit_dist: Path, rule: str) -> None:
    html = variant(lambda h: h.replace("</body>", f"<style>{rule}</style></body>", 1))
    assert refused(kit_dist, html).stage == "render"


# ── the second review: the end point is the solutions' property; a Kit page carries no CSS but the Kit's ─────────────────────────


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("va: k_va", "va: c_vb"),
        ("va: k_va", 'va: Synapse.constant(12.5, { label: "Other acid", unit: "cm3" })'),
        ("ma: 0.1, mb: k_mb", "ma: 0.2, mb: k_mb"),
    ],
    ids=["endpoint-follows-the-control", "endpoint-from-another-acid-volume", "endpoint-other-acid-strength"],
)
def test_an_end_point_that_follows_the_control_or_disagrees_with_the_concentration_is_refused(kit_dist: Path, old: str, new: str) -> None:
    e = refused(kit_dist, variant(lambda h: h.replace(old, new, 1)))
    assert e.stage == "render"
    assert e.rule in {"scene_ungrounded", "scene_scale", "plan_mismatch"}


@pytest.mark.parametrize(
    "rule",
    [
        ".syn-titration path{fill:var(--syn-indicator)}",
        ":root{--syn-indicator:#f7f8f4}",
        ".syn-titration rect:nth-of-type(3){y:20px;height:130px}",
        ".syn-eye-note{display:none}",
        "p{color:#333}",
    ],
    ids=["pink-flask", "kit-colour-redefined", "liquid-pinned", "note-hidden", "an-ordinary-rule"],
)
def test_a_kit_page_may_not_carry_any_stylesheet_of_its_own(kit_dist: Path, rule: str) -> None:
    e = refused(kit_dist, variant(lambda h: h.replace("</body>", f"<style>{rule}</style></body>", 1)))
    assert (e.stage, e.rule) == ("render", "forbidden_markup")


@pytest.mark.parametrize(
    "js",
    [
        'setInterval(function () { document.querySelector(".syn-titration path").setAttribute("fill-opacity", "0"); }, 20);',
        'setInterval(function () { document.querySelector(".syn-titration rect").setAttribute("visibility", "hidden"); }, 20);',
        'var r = document.createElementNS("http://www.w3.org/2000/svg", "rect"); r.setAttribute("width", "110"); r.setAttribute("height", "90"); r.setAttribute("fill", "#d6336c"); document.querySelector(".syn-titration").appendChild(r);',
        'var d = document.createElement("div"); d.setAttribute("popover", "manual"); d.textContent = "x"; document.body.appendChild(d); d.showPopover();',
        'document.getElementById("syn-style").sheet.insertRule(".syn-readout{display:none}", 0);',
        'var sh = new CSSStyleSheet(); sh.replaceSync(".syn-titration{opacity:.02}"); document.adoptedStyleSheets = [sh];',
    ],
    ids=["svg-fill-opacity", "svg-visibility", "svg-shape-added", "popover", "rule-inserted-into-the-kit-sheet", "constructed-stylesheet"],
)
def test_attribute_element_and_cssom_tricks_on_the_picture_are_refused(kit_dist: Path, js: str) -> None:
    # Building SVG by script is itself refused at the static scan; the rest are refused by the render's audit.
    assert refused(kit_dist, variant(before_ready(js))).stage in {"scan", "render"}


def test_a_hidden_decoy_sentence_does_not_stand_in_for_a_dead_eye(kit_dist: Path) -> None:
    js = (
        'var p = document.createElement("p"); p.hidden = true; p.setAttribute("data-synapse-eye-status", ""); p.textContent = "above below level"; document.body.insertBefore(p, document.body.firstChild);'
        'document.addEventListener("pointerdown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) e.stopImmediatePropagation(); }, true);'
        'document.addEventListener("keydown", function (e) { if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-synapse-eye")) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);'
    )
    assert refused(kit_dist, variant(before_ready(js))).stage == "render"


@pytest.mark.parametrize(("full", "start"), [("40.0", "10"), ("42.0", "10")], ids=["capacity-equals-the-range", "capacity-just-above"])
def test_a_burette_with_little_room_above_the_control_range_is_still_driven_and_minted(kit_dist: Path, full: str, start: str) -> None:
    """The harness drives the eye with the burette about half run in, so a capacity close to the control's maximum is not refused for being unable to show 'below'."""
    ok = mint(kit_dist, NAME, raw_html=variant(lambda h: h.replace("full: 50.0", f"full: {full}", 1)))
    assert ok.checked.controls_exercised == 1


def test_a_valve_with_two_steps_is_minted(kit_dist: Path) -> None:
    """Every stopcock check starts from the lowest position, so a valve with only two steps is not refused for running out of room."""
    html = variant(lambda h: h.replace('"min": 5.0, "max": 40.0, "value": 10.0, "grid": 7', '"min": 5.0, "max": 40.0, "value": 5.0, "grid": 2', 1)).replace("10 cm3 and 40 cm3", "two other volumes", 1)
    ok = mint(kit_dist, NAME, raw_html=html)
    assert ok.checked.controls_exercised == 1
