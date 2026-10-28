"""W17: the hands-on bench. A part's `drop` in the Plan, its checks (PLAN-022, D-70), the assembler (a snapped slider and the drop option), the overlay place for its item, and
the verifier's grounding of a grip (D-69)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api import kitmanifest
from api.i18n import overlay
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.pipeline.plan_checks import check
from api.verify.provenance import widget_problems

REPO = Path(__file__).resolve().parents[2]
HEAT = json.loads((REPO / "data/plans/physics-f4-specific_heat.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def changed(edit) -> dict:  # noqa: ANN001
    data = json.loads(json.dumps(HEAT))
    edit(data)
    return data


def issues(data: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [f"{i.code} {i.path}" for i in check(plan_module.Plan.model_validate(data), manifest)]


def test_the_specific_heat_bench_takes_cups_of_water_and_passes_every_check(manifest: kitmanifest.Manifest) -> None:
    plan = plan_module.Plan.model_validate(HEAT)
    assert plan.apparatus[0].drop is not None and plan.apparatus[0].drop.source == "mass"
    assert check(plan, manifest) == []
    html = assemble(plan, manifest).html
    assert '"snap": true' in html or "snap: true" in html
    assert 'drop: { value: c_mass, item: "Cup of water" }' in html


@pytest.mark.parametrize(
    ("edit", "why"),
    [
        (lambda d: d["apparatus"][0].update(drop={"source": "heat", "item": "Cup"}), "a model instance, not a slider"),
        (lambda d: d["apparatus"][0].update(drop={"source": "nothing", "item": "Cup"}), "no such control"),
        (lambda d: d["controls"][0].update(grid=9), "nine steps"),
        (lambda d: d["controls"][0].update(value=1.2), "starts between two items"),
        (lambda d: d["controls"][0].update(surface="dial"), "a dial, not a plain slider"),
        (lambda d: d["apparatus"][1].update(drop={"source": "mass", "item": "Cup"}), "two drops for one slider, and the thermometer shows nothing of it"),
    ],
)
def test_a_drop_that_cannot_work_is_refused(manifest: kitmanifest.Manifest, edit, why: str) -> None:  # noqa: ANN001
    found = issues(changed(edit), manifest)
    assert any(x.startswith("PLAN-022 apparatus[") and x.endswith(".drop") for x in found), (why, found)


def test_a_drop_on_a_part_that_shows_nothing_of_it_is_refused(manifest: kitmanifest.Manifest) -> None:
    data = changed(lambda d: d["apparatus"][2].update(drop={"source": "rise", "item": "Spoon"}))  # the burner draws the heat, which rise feeds, so this one is shown
    assert not any(x.endswith("apparatus[2].drop") for x in issues(data, manifest))
    data = changed(lambda d: (d["controls"][1].update(grid=6), d["apparatus"][0].update(drop={"source": "rise", "item": "Spoon"})))  # the beaker draws the mass only
    assert "PLAN-022 apparatus[0].drop" in issues(data, manifest)


def test_the_item_is_a_place_the_malay_overlay_fills() -> None:
    plan = plan_module.Plan.model_validate(HEAT)
    assert overlay.translatable(plan)["/apparatus/0/drop/item"] == "Cup of water"


def _audit(handle_chain: dict, drawn_chain: dict, control: str = "mass") -> dict:
    return {
        "controls": [{"id": "mass", "unit": "kg", "min": 0.5, "max": 4, "grid": 7}],
        "widgets": [
            {"kind": "apparatus", "id": "beaker-0.level", "chain": drawn_chain, "problems": [], "exact": [], "layout": [], "part": "beaker", "channel": "level", "channelType": "fraction", "units": [], "full": 4},
            {"kind": "handle", "id": "beaker-0.level", "control": control, "chain": handle_chain, "problems": [], "exact": [], "layout": []},
        ],
    }


def test_the_verifier_grounds_a_grip_on_the_control_its_channel_draws() -> None:
    mass = {"kind": "control", "id": "mass"}
    handle_rules = lambda a: [p.rule for p in widget_problems(a) if "handle" in p.reason]  # noqa: E731
    assert handle_rules(_audit(mass, mass)) == []
    assert handle_rules(_audit({"kind": "control", "id": "rise"}, mass)) == ["scene_ungrounded"]
    assert handle_rules(_audit(mass, {"kind": "control", "id": "rise"})) == ["scene_ungrounded"]
    assert handle_rules(_audit(mass, mass, control="ghost")) == ["scene_ungrounded"]
