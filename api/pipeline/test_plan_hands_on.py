"""W20 (D-80): every control a student varies is operated on the drawing. `draggable` names the controls that already are; `hands_on` gives the rest a graph whose
point is a handle, with no model call, and the result must still pass every plan check."""

from __future__ import annotations

from pathlib import Path

import pytest

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.plan_checks import check, draggable, hands_on

PLANS = sorted((Path(__file__).resolve().parents[2] / "data" / "plans").glob("*.json"))


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def load(name: str) -> plan_module.Plan:
    path = next(p for p in PLANS if p.stem.endswith(name))
    return plan_module.parse(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", PLANS, ids=[p.stem for p in PLANS])
def test_every_library_plan_is_already_hands_on_or_is_made_so_and_still_passes(path: Path, manifest: kitmanifest.Manifest) -> None:
    plan = plan_module.parse(path.read_text(encoding="utf-8"))
    upgraded = hands_on(plan, manifest)
    assert check(upgraded, manifest) == []
    assert len(upgraded.graphs) <= 2
    # nothing else about the Plan changes: only graphs are added, never removed or edited
    assert upgraded.graphs[: len(plan.graphs)] == plan.graphs
    assert upgraded.model_dump(exclude={"graphs"}) == plan.model_dump(exclude={"graphs"})


def test_a_control_left_as_a_bare_slider_gets_a_graph_whose_point_is_dragged(manifest: kitmanifest.Manifest) -> None:
    ohm = load("ohm_explorer")
    bare = ohm.model_copy(update={"graphs": []})
    left = {c.id for c in bare.controls} - draggable(bare, manifest)
    assert left, "the Ohm lab without its graph leaves a control that only a slider moves"
    upgraded = hands_on(bare, manifest)
    added = upgraded.graphs
    assert added and {g.x for g in added} <= left
    assert all(g.title.startswith("Drag the point") for g in added)
    assert check(upgraded, manifest) == []
    assert left - draggable(upgraded, manifest) == set() or len(added) == 2


def test_a_plan_that_is_already_hands_on_is_returned_unchanged(manifest: kitmanifest.Manifest) -> None:
    ready = [p for p in map(lambda path: plan_module.parse(path.read_text(encoding="utf-8")), PLANS) if {c.id for c in p.controls} <= draggable(p, manifest)]
    assert len(ready) >= 4  # the four demos at least
    for plan in ready:
        assert hands_on(plan, manifest) is plan, plan.id


def test_draggable_counts_surfaces_drops_and_graph_axes(manifest: kitmanifest.Manifest) -> None:
    hooke, gravity = load("hookes_amali"), load("planet_gravity")
    assert draggable(hooke, manifest)  # masses dropped on the hanger
    planets = next(c.id for c in gravity.controls if c.surface == "planets")
    assert planets in draggable(gravity, manifest)
