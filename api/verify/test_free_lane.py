"""The Free lane at the verifier (D-41): a whole page with no Kit is run in real Chromium and must meet the same page contract as a Kit page, minus the Kit
layers. Its readiness is decided by the harness (the page's own document loaded and painted), because the L0 scan forbids the `postMessage` a Kit-less page
would need to say it is ready. Nothing here can make a Free page `kit-verified`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from api.kit import latest_version
from api.pipeline.grounding import UNCHECKED_CITATION
from api.verify.conftest import ORIGIN, fixture_html
from api.verify.mint import VerificationFailed, VerifiedEnvironment, verify_environment

GOOD = fixture_html("free-pressure.html")


def free(kit_dist: Path, html: str = GOOD, **overrides: object) -> VerifiedEnvironment:
    args: dict = dict(
        slug="free_test",
        title="Pressure and depth",
        raw_html=html,
        lane="free",
        label="model-checked",
        kit_version=latest_version(kit_dist),
        citations=[UNCHECKED_CITATION],
        plan_summary="A page written whole by a model.",
        public_origin=ORIGIN,
        kit_dist=kit_dist,
        interaction_seconds=1.0,
        plan_models=None,
    )
    args.update(overrides)
    return verify_environment(**args)


def test_a_compliant_free_page_is_minted_as_the_free_lane_with_only_the_layers_that_examined_it(kit_dist: Path) -> None:
    env = free(kit_dist)
    assert env.lane == "free" and env.label == "model-checked"
    assert env.checked.layers == ("postprocess", "scan", "render")  # no provenance, grid or reference: no Kit examined anything
    assert env.checked.controls_exercised == 1 and env.checked.readouts == 1
    assert env.checked.models == () and env.checked.reference_cases == 0
    assert "/vendor/kit/" not in env.html


def test_the_wording_layer_is_claimed_only_when_the_caller_says_a_judge_passed_it(kit_dist: Path) -> None:
    assert free(kit_dist, wording_checked=True).checked.layers == ("postprocess", "scan", "render", "wording")
    assert "wording" not in free(kit_dist, wording_checked=False).checked.layers


def test_the_wording_flag_cannot_rescue_a_page_the_verifier_refuses(kit_dist: Path) -> None:
    bad = GOOD.replace("show();\n})();", 'show();\n  fetch("/x");\n})();')
    with pytest.raises(VerificationFailed) as err:
        free(kit_dist, bad, wording_checked=True)
    assert (err.value.stage, err.value.rule) == ("scan", "forbidden_api")


def test_a_free_page_can_never_be_kit_verified_or_canonical(kit_dist: Path) -> None:
    for label in ("kit-verified", "canonical", "reviewed"):
        with pytest.raises(VerificationFailed):
            free(kit_dist, label=label)


def swap(old: str, new: str) -> Callable[[str], str]:
    def edit(html: str) -> str:
        assert old in html, f"the good page no longer contains {old!r}"
        return html.replace(old, new, 1)

    return edit


NAVIGATE = swap("depth.addEventListener(\"input\", show);", "depth.addEventListener(\"input\", show);\n  document.addEventListener('pointerdown', function () { window['loc' + 'ation'] = '//evil.example/p'; });")

REFUSED: list[tuple[str, Callable[[str], str], str, str]] = [
    ("fetch", swap("show();\n})();", 'show();\n  fetch("/x");\n})();'), "scan", "forbidden_api"),
    (
        "an absolute URL, even an xmlns",
        swap("<h1>", '<svg xmlns="http://www.w3.org/2000/svg" aria-label="drawing"></svg><h1>'),
        "scan",
        "forbidden_api",
    ),
    ("postMessage, which only the Kit may use", swap("show();\n})();", "show();\n  window.postMessage('x', '*');\n})();"), "scan", "forbidden_api"),
    (
        "a control with no accessible name",
        lambda h: swap('<label for="depth">Depth h in metres</label>', "")(swap(' aria-label="Depth in metres"', "")(h)),
        "render",
        "a11y",
    ),
    ("a control that changes no readout", swap('out.textContent = pressureKpa(h).toFixed(1) + " kPa";', 'out.textContent = "fixed";'), "render", "dead_control"),
    ("an operable element that is not a declared control", swap("</output>", "</output><button>Go</button>"), "render", "undeclared_control"),
    ("a control under 44 px", swap("min-height: 44px", "min-height: 20px"), "render", "touch_target"),
    ("content wider than the phone", swap("<h1>", '<div style="width:600px">wide</div><h1>'), "render", "horizontal_overflow"),
    ("an uncaught error", swap("show();\n})();", 'show();\n  throw new Error("boom");\n})();'), "render", "errors"),
    (
        "something that animates under reduced motion",
        swap("</style>", "@keyframes a { from { opacity: 0.5; } to { opacity: 1; } } h1 { animation: a 100s infinite; }\n</style>"),
        "render",
        "a11y",
    ),
    ("no document language", swap('<html lang="en">', "<html>"), "render", "a11y"),
    ("a navigation on the first press", NAVIGATE, "render", "navigation"),
    ("words drawn by CSS generated content", swap("</style>", "h1::after { content: 'Hooke was wrong'; }\n</style>"), "scan", "free_lane_scan"),
    ("a CSS pseudo-element", swap("</style>", "p::before { color: red; }\n</style>"), "scan", "free_lane_scan"),
    ("numbers drawn by CSS counters", swap("</style>", "body { counter-reset: n 7; }\n</style>"), "scan", "free_lane_scan"),
    ("an image, which the reader cannot read", swap("<h1>", '<img alt="a graph" src="data:image/png;base64,AAAA"><h1>'), "scan", "free_lane_scan"),
    ("a custom font", swap("</style>", "@font-face { font-family: x; }\n</style>"), "scan", "free_lane_scan"),
    ("the harness's own names", swap("show();\n})();", "show();\n  var t = window.__synapse;\n})();"), "scan", "free_lane_scan"),
    ("test-browser detection", swap("show();\n})();", "show();\n  var t = navigator.webdriver;\n})();"), "scan", "free_lane_scan"),
    ("a Kit action marker written in the markup", swap("</output>", '</output><span data-synapse-action="x"></span>'), "scan", "free_lane_scan"),
    (
        "a button given the Kit action marker by script (no exemption outside the Kit lane)",
        swap(
            "show();\n})();",
            "show();\n  var b = document.createElement('button'); b.textContent = 'Go'; b.setAttribute('data-synapse-' + 'action', ''); document.body.appendChild(b);\n})();",
        ),
        "render",
        "undeclared_control",
    ),
]


@pytest.mark.parametrize("name,edit,stage,rule", REFUSED, ids=[r[0] for r in REFUSED])
def test_a_free_page_that_breaks_the_page_contract_is_refused_at_its_named_rule(
    kit_dist: Path, name: str, edit: Callable[[str], str], stage: str, rule: str
) -> None:
    with pytest.raises(VerificationFailed) as err:
        free(kit_dist, edit(GOOD))
    assert (err.value.stage, err.value.rule) == (stage, rule), f"{name}: {err.value}"


def test_a_free_page_cannot_see_the_flag_that_tells_the_kit_it_is_being_verified(kit_dist: Path) -> None:
    """The Kit reads `window.__SYNAPSE_VERIFY__`; a Kit-less page must not. Here the page looks the flag up with a name the static scan cannot see (it is built at
    run time). If the harness exposed the flag, the page would freeze its readout and be refused as a dead control; it is not exposed, so the page is minted."""
    probing = GOOD.replace(
        "function show() {",
        "function show() {\n    if (window['__SYN' + 'APSE_VERIFY__']) { out.textContent = 'frozen'; return; }",
    )
    assert "__SYN' + 'APSE_VERIFY__" in probing
    assert free(kit_dist, probing).lane == "free"


def test_the_kit_lane_still_gets_the_flag_it_reads(kit_dist: Path) -> None:
    from api.verify.conftest import mint

    assert mint(kit_dist).label == "model-checked"  # the reference Kit page is verified exactly as before


def test_the_free_limits_line_is_honest_about_what_the_browser_run_covers(kit_dist: Path, tmp_path: Path) -> None:
    from api.verify.gate import deliver
    from api.verify.store import SqliteEnvironmentStore

    for i, reader in enumerate((True, False)):
        store = SqliteEnvironmentStore(tmp_path / f"envs{i}.db")  # a store never replaces a row, and the same page is minted twice here
        env = free(kit_dist, wording_checked=reader)
        store.put_verified(env)
        limits = deliver(store, env.env_id, public_origin=ORIGIN, kit_dist=kit_dist).checked.limits
        assert limits.startswith("Written whole by a model") and "short, scripted stretch of time" in limits
        assert ("a second model read" in limits) is reader
        assert "Check it against your textbook" in limits


# W17 (D-71): a model-written page may draw handles for its sliders. The harness drags each one; a handle that moves nothing, or names no slider, is refused.
_GRIP = '<div id="grip" data-synapse-handle="depth" aria-hidden="true" style="width:48px;height:48px;border-radius:24px;background:#0a7;touch-action:none;cursor:grab"></div>\n'
_DRAG = """
  var grip = document.getElementById("grip");
  var held = false;
  grip.addEventListener("pointerdown", function (e) { held = true; grip.setPointerCapture(e.pointerId); });
  grip.addEventListener("pointermove", function (e) {
    if (!held) return;
    var r = grip.parentElement.getBoundingClientRect();
    var f = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    depth.value = String(Math.round(f * 20) / 2);
    depth.dispatchEvent(new Event("input", { bubbles: true }));
  });
  grip.addEventListener("pointerup", function () { held = false; });
  show();
})();"""


def _with_grip(html: str, script: bool = True, name: str = "depth") -> str:
    out = html.replace('<output data-synapse-readout="pressure"', _GRIP.replace('"depth"', f'"{name}"') + '<output data-synapse-readout="pressure"', 1)
    return out.replace("  show();\n})();", _DRAG, 1) if script else out


def test_a_free_page_with_a_working_handle_is_minted(kit_dist: Path) -> None:
    assert free(kit_dist, _with_grip(GOOD)).lane == "free"


@pytest.mark.parametrize("html", [_with_grip(GOOD, script=False), _with_grip(GOOD, name="nothing")], ids=["dead", "orphan"])
def test_a_free_page_whose_handle_moves_nothing_or_names_no_slider_is_refused(kit_dist: Path, html: str) -> None:
    with pytest.raises(VerificationFailed) as err:
        free(kit_dist, html)
    assert (err.value.stage, err.value.rule) == ("render", "handle_dead")
