"""W4 stage 4: Newton's cannonball in the verifier (L1 to L3 and the harness). The reference bench is minted; a scene bound to anything but a km/s control and Earth's two speeds fed by one
radius, a control that cannot show all four outcomes, and a page that redraws, relabels, hides, restyles or adds words to the picture are refused. Real Chromium."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from api.verify.conftest import fixture_html, mint
from api.verify.mint import VerificationFailed, VerifiedEnvironment

NAME = "reference-orbit.html"
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


def test_the_cannonball_bench_is_minted_with_all_three_models_and_the_scene(minted: VerifiedEnvironment) -> None:
    assert minted.checked.layers[:3] == ("postprocess", "scan", "render")
    assert "provenance" in minted.checked.layers and "grid" in minted.checked.layers and "reference" in minted.checked.layers
    assert ("physics.circular_speed", (("central_mass", 5.972e24),)) in minted.checked.models
    assert ("physics.escape_speed", (("central_mass", 5.972e24),)) in minted.checked.models
    assert ("physics.centripetal_acceleration", ()) in minted.checked.models
    assert "Synapse.orbitScene" in minted.html


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("speed: c_launch", "speed: Synapse.observable(7)"),
        ("speed: c_launch", "speed: m_circular"),
        ("circular: m_circular", "circular: Synapse.observable(7.9)"),
        ("circular: m_circular, escape: m_escape", "circular: m_escape, escape: m_circular"),
        ("escape: m_escape", "escape: m_circular"),
        ("escape: m_escape", "escape: m_centripetal"),
        ("escape: m_escape", "escape: Synapse.escapeSpeed({ central_mass: 5.972e+24, radius: Synapse.constant(6371.0, { label: 'A second radius', unit: 'km' }) })"),
        ("full: 15.0", "full: 14.0"),
        ("full: 15.0", "full: 400.0"),
    ],
    ids=["free-speed", "model-as-speed", "free-circular", "swapped", "escape-is-circular", "escape-is-centripetal", "two-radii", "scale-too-small", "scale-huge"],
)
def test_a_scene_bound_to_anything_but_a_km_per_s_control_and_earths_two_speeds_is_refused(kit_dist: Path, old: str, new: str) -> None:
    assert refused(kit_dist, variant(lambda h: h.replace(old, new, 1))).stage == "render"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Synapse.constant(6371.0,", "Synapse.constant(1737.0,"),  # the Moon's radius
        ("central_mass: 5.972e+24, radius: k_radius });\n  var m_escape", "central_mass: 6.4e+23, radius: k_radius });\n  var m_escape"),
    ],
    ids=["moons-radius", "another-mass-on-one-model"],
)
def test_a_scene_about_anything_but_earth_is_refused(kit_dist: Path, old: str, new: str) -> None:
    assert old in fixture_html(NAME)
    assert refused(kit_dist, variant(lambda h: h.replace(old, new, 1))).stage == "render"


def test_a_control_that_can_never_show_one_of_the_four_outcomes_is_refused(kit_dist: Path) -> None:
    # 8.5 to 15 km/s never falls back or circles (the circular speed is 7.91 km/s)
    html = variant(lambda h: h.replace('"min": 1.0, "max": 15.0, "value": 5.0, "grid": 28', '"min": 8.5, "max": 15.0, "value": 9.0, "grid": 13', 1))
    assert refused(kit_dist, html).stage in {"render", "provenance"}
    # 1 to 11 km/s never escapes (the escape speed is 11.19 km/s)
    html = variant(lambda h: h.replace('"min": 1.0, "max": 15.0, "value": 5.0, "grid": 28', '"min": 1.0, "max": 11.0, "value": 5.0, "grid": 20', 1).replace("full: 15.0", "full: 11.0", 1))
    assert refused(kit_dist, html).stage in {"render", "provenance"}


@pytest.mark.parametrize(
    "tamper",
    [
        'document.querySelector(".syn-orbit-scene path").setAttribute("d", "M 130 64 L 131 65");',
        'document.querySelector(".syn-orbit-scene path").setAttribute("stroke", "var(--syn-bg)");',
        'document.querySelector(".syn-orbit-scene").setAttribute("aria-label", "The cannonball lands on Earth.");',
        'document.querySelector(".syn-orbit-scene text").textContent = "Moon";',
        'document.querySelector("[data-synapse-observations]").textContent = "The cannonball escapes.";',
        'document.querySelector(".syn-orbit-scene").style.visibility = "hidden";',
        'document.querySelector(".syn-orbit-scene circle").setAttribute("fill-opacity", "0");',
        'document.querySelector(".syn-orbit-scene polygon").setAttribute("points", "0,0 1,1 2,2");',
    ],
    ids=["path-redrawn", "path-hidden-by-colour", "relabelled", "earth-renamed", "sentence-rewritten", "hidden", "earth-faded", "mountain-moved"],
)
def test_an_orbit_scene_a_page_redraws_relabels_or_hides_is_refused(kit_dist: Path, tamper: str) -> None:
    js = f"setInterval(function () {{ {tamper} }}, 20);"
    assert refused(kit_dist, variant(before_ready(js))).stage == "render"


@pytest.mark.parametrize(
    "rule",
    [".syn-orbit-scene path{stroke:red}", ".syn-orbit-note{display:none}", ":root{--syn-liquid:#ffffff}"],
    ids=["path-recoloured", "sentence-hidden", "earth-colour-redefined"],
)
def test_a_kit_page_may_not_carry_any_stylesheet_of_its_own(kit_dist: Path, rule: str) -> None:
    e = refused(kit_dist, variant(lambda h: h.replace("</body>", f"<style>{rule}</style></body>", 1)))
    assert e.stage == "render" and e.rule in {"forbidden_markup", "harness_error"}


def test_a_page_made_drawing_or_words_inside_the_scene_are_refused(kit_dist: Path) -> None:
    assert refused(kit_dist, variant(before_ready('var f = document.querySelector(".syn-orbit-scene"); var r = document.createElementNS(f.namespaceURI, "rect"); r.setAttribute("width", "260"); r.setAttribute("height", "240"); f.appendChild(r);'))).stage == "render"
    assert refused(kit_dist, variant(before_ready('document.querySelector(".syn-orbit").appendChild(document.createTextNode("Everything here is certain."));'))).stage == "render"


def test_a_page_that_swaps_which_speed_feeds_which_readout_is_refused(kit_dist: Path) -> None:
    def swap(h: str) -> str:
        return h.replace("value: m_circular", "value: @@", 1).replace("value: m_escape", "value: m_circular", 1).replace("value: @@", "value: m_escape", 1)

    e = refused(kit_dist, variant(swap))
    assert (e.stage, e.rule) == ("render", "plan_mismatch")
