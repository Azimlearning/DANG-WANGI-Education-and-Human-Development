"""W4: the harness really drags the masses of a `massHanger` (L2). The mass bench is minted; a page whose masses do nothing is refused as `drag_dead`; a forged mass or a mass
named with a number is refused by the audit. Real Chromium, real mouse and keyboard."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from api.verify.conftest import fixture_html, mint
from api.verify.mint import VerificationFailed, VerifiedEnvironment

NAME = "reference-masses.html"
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


def test_the_mass_bench_is_minted_with_its_control_swept_and_its_masses_driven(minted: VerifiedEnvironment) -> None:
    assert minted.checked.layers[:3] == ("postprocess", "scan", "render")
    assert "provenance" in minted.checked.layers and "grid" in minted.checked.layers and "reference" in minted.checked.layers
    assert minted.checked.controls_exercised == 1
    assert minted.checked.grid_points >= 6  # the five-mass control's positions, 0 to 10 N in steps of 2 N
    assert ("mechanics.hookes", (("k", 50.0),)) in minted.checked.models
    assert "Synapse.massHanger" in minted.html and "Synapse.springScene" in minted.html


def test_a_page_that_swallows_every_pointerdown_has_masses_that_cannot_be_dragged(kit_dist: Path) -> None:
    e = refused(kit_dist, variant(before_ready('document.addEventListener("pointerdown", function (e) { e.stopImmediatePropagation(); }, true);')))
    assert (e.stage, e.rule) == ("render", "drag_dead")
    assert "onto the hanger" in e.reason


def test_a_page_that_swallows_every_click_has_masses_that_cannot_be_pressed_from_the_keyboard(kit_dist: Path) -> None:
    e = refused(kit_dist, variant(before_ready('document.addEventListener("click", function (e) { e.stopImmediatePropagation(); }, true);')))
    assert (e.stage, e.rule) == ("render", "drag_dead")
    assert "keyboard" in e.reason


def test_a_page_that_stops_the_masses_reaching_the_control_is_refused(kit_dist: Path) -> None:
    js = 'Array.from(document.querySelectorAll("[data-synapse-drag=load]")).forEach(function (m) { m.addEventListener("pointerup", function (e) { e.stopImmediatePropagation(); }, true); });'
    e = refused(kit_dist, variant(before_ready(js)))
    assert (e.stage, e.rule) == ("render", "drag_dead")


def test_a_mass_a_page_made_itself_is_refused_as_a_forged_action(kit_dist: Path) -> None:
    e = refused(kit_dist, variant(lambda h: h.replace("</body>", '<button data-synapse-action="drag" data-synapse-drag="load">Mass Z</button>\n</body>', 1)))
    assert e.stage == "render"


def test_a_mass_named_with_a_number_the_kit_did_not_set_is_refused(kit_dist: Path) -> None:
    js = 'document.querySelector("[data-synapse-drag=load]").setAttribute("aria-label", "Mass A weighs 9.81 N");'
    assert refused(kit_dist, variant(before_ready(js))).stage == "render"


def test_a_page_with_no_masses_is_not_asked_to_drag_anything(kit_dist: Path) -> None:
    """The reference spring page has a slider only: the drag step finds nothing and adds no refusal."""
    assert mint(kit_dist, "reference-spring.html").label == "model-checked"


# ── the harness takes what must exist from the Kit's audit, drives every mass, and touches ──────────────────────────────────────


def test_a_page_that_blocks_every_mass_but_the_first_is_refused(kit_dist: Path) -> None:
    js = 'document.addEventListener("pointerdown", function (e) { var t = e.target; if (t && t.getAttribute && t.getAttribute("data-synapse-drag") && t.textContent !== "A") e.stopImmediatePropagation(); }, true);'
    e = refused(kit_dist, variant(before_ready(js)))
    assert (e.stage, e.rule) == ("render", "drag_dead")
    assert "mass 2 of 5" in e.reason


def test_a_page_that_blocks_only_a_finger_is_refused(kit_dist: Path) -> None:
    js = 'document.addEventListener("pointerdown", function (e) { if (e.pointerType === "touch") e.stopImmediatePropagation(); }, true);'
    e = refused(kit_dist, variant(before_ready(js)))
    assert (e.stage, e.rule) == ("render", "drag_dead")
    assert "finger" in e.reason


def test_a_page_that_renames_its_masses_to_hide_them_from_the_harness_is_refused(kit_dist: Path) -> None:
    js = (
        'Array.from(document.querySelectorAll("[data-synapse-drag]")).forEach(function (m) { m.removeAttribute("data-synapse-drag"); });'
        'document.addEventListener("pointerdown", function (e) { e.stopImmediatePropagation(); }, true);'
    )
    e = refused(kit_dist, variant(before_ready(js)))
    assert e.stage == "render"


def test_a_page_that_hides_or_moves_a_mass_is_refused_by_the_audit(kit_dist: Path) -> None:
    hide = 'setInterval(function () { document.querySelectorAll("[data-synapse-drag]")[1].style.display = "none"; }, 20);'
    assert refused(kit_dist, variant(before_ready(hide))).stage == "render"
    move = 'setInterval(function () { document.querySelectorAll("[data-synapse-drag]")[2].style.transform = "translate(700px, 0)"; }, 20);'
    assert refused(kit_dist, variant(before_ready(move))).stage == "render"


def test_a_script_that_sets_an_off_step_load_is_snapped_to_a_whole_number_of_masses_not_refused(kit_dist: Path) -> None:
    ok = mint(kit_dist, NAME, raw_html=variant(before_ready("c_load.set(2.9);")))
    assert ok.checked.controls_exercised == 1


@pytest.mark.parametrize(
    "extension",
    ["Synapse.observable(0.1)", "c_load", "m_spring.map(function (v) { return v * 2; })"],
    ids=["free-observable", "the-control", "a-map-of-the-model"],
)
def test_a_scene_bound_to_anything_but_the_hookes_output_is_refused(kit_dist: Path, extension: str) -> None:
    html = variant(lambda h: h.replace("extension: m_spring, full: 0.25", f"extension: {extension}, full: 0.25", 1))
    assert refused(kit_dist, html).stage == "render"


@pytest.mark.parametrize(
    "tamper",
    [
        'document.querySelector(".syn-scene polyline").setAttribute("points", "0,0 160,250");',
        'document.querySelector(".syn-scene").setAttribute("aria-label", "A spring that is not stretched at all.");',
        'document.querySelector(".syn-scene").style.visibility = "hidden";',
    ],
    ids=["redrawn", "relabelled", "hidden"],
)
def test_a_scene_a_page_redraws_relabels_or_hides_is_refused(kit_dist: Path, tamper: str) -> None:
    js = f"setInterval(function () {{ {tamper} }}, 20);"
    e = refused(kit_dist, variant(before_ready(js)))
    assert e.stage == "render"
