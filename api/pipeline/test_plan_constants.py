"""PLAN-020: a constant the textbooks fix must carry a value the textbooks use."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api import kitmanifest
from api.kit import latest_version
from api.pipeline import constants as known_constants
from api.pipeline import plan_checks as pc
from api.pipeline.plan import Plan

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def pressure() -> dict:
    return json.loads((REPO / "data" / "plans" / "physics-f5-pressure_depth.json").read_text(encoding="utf-8"))


def codes(d: dict, manifest: kitmanifest.Manifest) -> list[str]:
    return [i.code for i in pc.check(Plan.model_validate(d), manifest)]


def test_the_golden_value_of_g_passes(manifest: kitmanifest.Manifest) -> None:
    assert "PLAN-020" not in codes(pressure(), manifest)


def test_g_of_ten_is_refused_and_the_hint_names_the_textbook_value(manifest: kitmanifest.Manifest) -> None:
    d = pressure()
    d["models"][0]["params"]["g"] = 10.0
    issues = pc.check(Plan.model_validate(d), manifest)
    hits = [i for i in issues if i.code == "PLAN-020"]
    assert len(hits) == 1
    assert hits[0].path == "models[0].params.g"
    assert "9.81" in hits[0].hint and "m/s2" in hits[0].hint


def test_the_rounded_9_8_is_accepted(manifest: kitmanifest.Manifest) -> None:
    d = pressure()
    d["models"][0]["params"]["g"] = 9.8
    assert "PLAN-020" not in codes(d, manifest)


def test_both_molar_volumes_are_accepted_and_others_refused(manifest: kitmanifest.Manifest) -> None:
    d = json.loads((REPO / "data" / "plans" / "chemistry-f4-gas_volume.json").read_text(encoding="utf-8"))
    assert "PLAN-020" not in codes(d, manifest)
    for m in d["models"]:
        if "molar_volume" in m["params"]:
            m["params"]["molar_volume"] = 22.0
    assert "PLAN-020" in codes(d, manifest)


def test_a_constant_with_a_known_id_and_unit_is_checked(manifest: kitmanifest.Manifest) -> None:
    d = pressure()
    d["constants"] = [{"id": "g", "label": "Gravity", "unit": "m/s2", "value": 10.0}]
    assert "PLAN-020" in codes(d, manifest)
    d["constants"] = [{"id": "g", "label": "Gravity", "unit": "m/s2", "value": 9.81}]
    assert "PLAN-020" not in codes(d, manifest)


def test_a_constant_in_another_unit_is_left_alone(manifest: kitmanifest.Manifest) -> None:
    d = pressure()
    d["constants"] = [{"id": "g", "label": "Mass", "unit": "kg", "value": 3.0}]
    assert "PLAN-020" not in codes(d, manifest)


def test_every_table_entry_has_a_value_and_a_way_to_be_found() -> None:
    for k in known_constants.KNOWN:
        assert k.accepted and (k.models or k.ids)
        assert known_constants.is_accepted(k, k.accepted[0])
        assert not known_constants.is_accepted(k, k.accepted[0] * 1.5)
