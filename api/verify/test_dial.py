"""W4 stage 3: the harness really turns a dial (L2). The fermentation bench is minted; a dial that does not follow the pointer, or whose arrow keys are dead, is refused (`dial_dead`);
a scene drawn from the wrong model, fed by another amount, redrawn, relabelled or restyled by the page is refused. Real Chromium, real mouse, keyboard and touch."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from api.verify.conftest import fixture_html, mint
from api.verify.mint import VerificationFailed, VerifiedEnvironment

NAME = "reference-fermentation.html"
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


def test_the_fermentation_bench_is_minted_with_its_dial_turned_and_its_keys_pressed(minted: VerifiedEnvironment) -> None:
    assert minted.checked.layers[:3] == ("postprocess", "scan", "render")
    assert "provenance" in minted.checked.layers and "grid" in minted.checked.layers and "reference" in minted.checked.layers
    assert minted.checked.controls_exercised == 1
    assert ("biology.respiration_energy", (("energy_per_mole", 210.0),)) in minted.checked.models
    assert ("biology.respiration_energy", (("energy_per_mole", 2898.0),)) in minted.checked.models
    assert "Synapse.dial" in minted.html and "Synapse.fermentationScene" in minted.html


@pytest.mark.parametrize(
    ("js", "needle"),
    [
        ('document.addEventListener("pointerdown", function (e) { e.stopImmediatePropagation(); }, true);', "mouse"),
        ('document.addEventListener("pointerdown", function (e) { if (e.pointerType === "touch") e.stopImmediatePropagation(); }, true);', "finger"),
        ('document.addEventListener("keydown", function (e) { e.preventDefault(); e.stopImmediatePropagation(); }, true);', "arrow"),
        ('document.addEventListener("pointermove", function (e) { e.stopImmediatePropagation(); }, true);', "mouse"),
    ],
    ids=["pointer-swallowed", "finger-swallowed", "keys-swallowed", "moves-swallowed"],
)
def test_a_dial_the_page_made_dead_is_refused(kit_dist: Path, js: str, needle: str) -> None:
    e = refused(kit_dist, variant(before_ready(js)))
    assert (e.stage, e.rule) == ("render", "dial_dead")
    assert needle in e.reason


def test_a_dial_the_page_made_itself_is_refused(kit_dist: Path) -> None:
    assert refused(kit_dist, variant(lambda h: h.replace("</body>", '<div data-synapse-dial="glucose" class="syn-dial"></div>\n</body>', 1))).stage == "render"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("fermented: c_glucose", "fermented: Synapse.observable(0.002)"),
        ("fermented: c_glucose", "fermented: m_ferment"),
        ("energy: m_ferment", "energy: Synapse.observable(1)"),
        ("energy: m_ferment", "energy: c_glucose"),
        ("energy: m_ferment", "energy: Synapse.respirationEnergy({ energy_per_mole: 210.0, glucose: Synapse.constant(0.003, { label: 'Another amount', unit: 'mol' }) })"),
        ("full: 0.004", "full: 0.003"),
        ("full: 0.004", "full: 0.5"),
    ],
    ids=["free-amount", "model-as-amount", "free-energy", "control-as-energy", "energy-of-another-amount", "capacity-too-small", "capacity-huge"],
)
def test_a_scene_bound_to_anything_but_a_mol_control_and_its_own_energy_is_refused(kit_dist: Path, old: str, new: str) -> None:
    assert refused(kit_dist, variant(lambda h: h.replace(old, new, 1))).stage == "render"


@pytest.mark.parametrize(
    "tamper",
    [
        'var c = Array.from(document.querySelectorAll(".syn-fermentation rect")).filter(function (r) { return r.getAttribute("fill") === "var(--syn-card)"; }); c[0].setAttribute("fill", "var(--syn-cloud)");',
        'document.querySelector(".syn-fermentation circle").setAttribute("r", "9");',
        'document.querySelector(".syn-fermentation").setAttribute("aria-label", "Nothing at all has happened.");',
        'document.querySelector(".syn-fermentation text").textContent = "B";',
        'document.querySelector("[data-synapse-observations]").textContent = "Tube B bubbles.";',
        'document.querySelector(".syn-fermentation").style.visibility = "hidden";',
        'document.querySelector(".syn-fermentation rect").setAttribute("fill-opacity", "0");',
    ],
    ids=["tube-b-cloud-forced", "bubble-resized", "relabelled", "tubes-swapped", "sentence-rewritten", "hidden", "fill-opacity"],
)
def test_a_fermentation_scene_a_page_redraws_relabels_or_hides_is_refused(kit_dist: Path, tamper: str) -> None:
    js = f"setInterval(function () {{ {tamper} }}, 20);"
    assert refused(kit_dist, variant(before_ready(js))).stage == "render"


@pytest.mark.parametrize(
    "rule",
    [
        ".syn-fermentation circle{fill:red}",
        ":root{--syn-cloud:#ffffff}",
        ".syn-dial{display:none}",
        ".syn-ferment-note{display:none}",
    ],
    ids=["bubbles-recoloured", "cloud-colour-redefined", "dial-hidden", "sentence-hidden"],
)
def test_a_kit_page_may_not_carry_any_stylesheet_of_its_own(kit_dist: Path, rule: str) -> None:
    e = refused(kit_dist, variant(lambda h: h.replace("</body>", f"<style>{rule}</style></body>", 1)))
    # A style rule that hides the dial leaves the harness nothing to turn, which it reports first; every other rule is the audit's `forbidden_markup`.
    assert e.stage == "render"
    assert e.rule in {"forbidden_markup", "harness_error"}


def test_a_dial_with_two_steps_and_a_scene_with_room_to_spare_are_minted(kit_dist: Path) -> None:
    html = variant(lambda h: h.replace('"value": 0.001, "grid": 8', '"value": 0.0, "grid": 2', 1).replace("full: 0.004", "full: 0.006", 1))
    ok = mint(kit_dist, NAME, raw_html=html)
    assert ok.checked.controls_exercised == 1


# ── the review: the pathway is pinned, a page cannot overlay the scene or add words, swapped instances are caught, real keys are checked ────────────────


def test_a_scene_for_any_other_pathway_than_alcohol_fermentation_is_refused(kit_dist: Path) -> None:
    """The picture (bubbles, cloudy limewater, a warmer tube, ethanol) is false for lactic acid fermentation (150 kJ per mole) and for aerobic respiration (2898)."""
    for per_mole in ("150.0", "2898.0"):
        html = variant(lambda h, v=per_mole: h.replace("energy_per_mole: 210.0", f"energy_per_mole: {v}", 1).replace("210 kJ", f"{v.removesuffix('.0')} kJ", 1))
        assert refused(kit_dist, html).stage == "render"


def test_a_page_made_drawing_cannot_paint_over_the_scene(kit_dist: Path) -> None:
    assert refused(kit_dist, variant(before_ready('var f = document.querySelector(".syn-ferment"); var ns = f.querySelector("svg").namespaceURI; var s = document.createElementNS(ns, "svg"); s.setAttribute("width", "1"); s.setAttribute("height", "1"); s.setAttribute("overflow", "visible"); s.setAttribute("pointer-events", "none"); var r = document.createElementNS(ns, "rect"); var b = f.getBoundingClientRect(); r.setAttribute("width", String(b.width)); r.setAttribute("height", String(b.height)); r.setAttribute("fill", "var(--syn-card)"); s.appendChild(r); f.parentNode.insertBefore(s, f.nextSibling);'))).stage in {"scan", "render"}


def test_words_a_page_adds_inside_the_scene_are_refused(kit_dist: Path) -> None:
    assert refused(kit_dist, variant(before_ready('document.querySelector(".syn-ferment").appendChild(document.createTextNode("Tube A: the limewater stays clear; yeast gives off no gas."));'))).stage == "render"


def test_a_page_that_swaps_which_energy_feeds_which_readout_is_refused(kit_dist: Path) -> None:
    def swap(h: str) -> str:
        return h.replace("value: m_ferment", "value: @@", 1).replace("value: m_aerobic", "value: m_ferment", 1).replace("value: @@", "value: m_aerobic", 1)

    e = refused(kit_dist, variant(swap))
    assert (e.stage, e.rule) == ("render", "plan_mismatch")


def test_a_page_that_blocks_real_key_presses_on_the_dials_range_input_is_refused(kit_dist: Path) -> None:
    """The sweep sets the input with untrusted events, so only a real key press shows that a student's arrow keys reach the Kit."""
    e = refused(kit_dist, variant(before_ready('document.addEventListener("input", function (e) { if (e.isTrusted && e.target && e.target.type === "range") e.stopImmediatePropagation(); }, true);')))
    assert (e.stage, e.rule) == ("render", "dial_dead")
