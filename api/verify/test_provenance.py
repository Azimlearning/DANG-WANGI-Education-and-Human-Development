"""L1 and L3 as pure functions, with forged audits: no browser needed. Also the independent references."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from api.verify import provenance as p
from api.verify.references import REFERENCES, evaluate_model


def good_audit() -> dict:
    """What the Kit reports for the spring fixture at load = 2 N, k = 50 N/m."""
    return {
        "kitVersion": "0.1.0",
        "intact": True,
        "controls": [
            {
                "id": "load",
                "label": "Load",
                "unit": "N",
                "min": 0,
                "max": 10,
                "grid": 10,
                "default": 2,
                "step": 1,
                "value": 2,
                "inputValue": "2",
            }
        ],
        "readouts": [
            {
                "label": "Extension",
                "unit": "m",
                "digits": 3,
                "value": 0.04,
                "displayed": "0.040 m",
                "expected": "0.040 m",
                "chain": {
                    "kind": "model",
                    "id": "mechanics.hookes",
                    "params": {"k": 50},
                    "inputs": {
                        "load": {"kind": "control", "id": "load", "min": 0, "max": 10, "grid": 10, "default": 2}
                    },
                },
            }
        ],
        "constants": [],
        "copy": [
            {"text": "Why does a spring stretch?", "numbers": []},
            {"text": "Hang a load on a spring.", "numbers": []},
        ],
        "readoutElements": 1,
        "series": [],
        "actions": [],
        "forgedActions": 0,
        "ownedMismatches": [],
        "unownedNumbers": [],
        "unownedAttributeNumbers": [],
        "forbidden": [],
        "shadowRoots": 0,
    }


def rules(problems: list[p.Problem]) -> list[str]:
    return [x.rule for x in problems]


def test_a_good_audit_has_no_l1_or_l3_problems() -> None:
    audit = good_audit()
    assert p.l1_problems(audit) == []
    problems, compared = p.l3_problems(audit)
    assert problems == []
    assert compared == 1
    assert p.plan_problems(audit, [{"id": "mechanics.hookes", "params": {"k": 50}}]) == []


@pytest.mark.parametrize("bad", [None, "nope", 3, []])
def test_a_missing_or_malformed_audit_is_kit_missing(bad) -> None:
    assert rules(p.l1_problems(bad)) == ["kit_missing"]


def test_a_replaced_window_synapse_is_refused() -> None:
    audit = good_audit() | {"intact": False}
    assert "kit_not_intact" in rules(p.l1_problems(audit))


def test_a_readout_on_a_free_observable_is_ungrounded() -> None:
    audit = good_audit()
    audit["readouts"][0]["chain"] = {"kind": "free"}
    assert rules(p.l1_problems(audit)) == ["ungrounded_readout"]


def test_arithmetic_written_in_the_page_is_refused_even_on_top_of_a_model() -> None:
    audit = good_audit()
    inner = audit["readouts"][0]["chain"]
    audit["readouts"][0]["chain"] = {"kind": "derived", "user": True, "inputs": {"x": inner}}
    assert rules(p.l1_problems(audit)) == ["unaudited_arithmetic"]


def test_a_unit_conversion_on_a_model_is_allowed_and_checked() -> None:
    audit = good_audit()
    inner = audit["readouts"][0]["chain"]
    audit["readouts"][0].update(
        unit="mm",
        digits=1,
        value=40.0,
        displayed="40.0 mm",
        expected="40.0 mm",
        chain={"kind": "convert", "from": "m", "to": "mm", "factor": 1000, "inputs": {"x": inner}},
    )
    assert p.l1_problems(audit) == []
    problems, compared = p.l3_problems(audit)
    assert problems == [] and compared == 1


def test_a_model_with_no_reference_is_refused() -> None:
    audit = good_audit()
    audit["readouts"][0]["chain"]["id"] = "mechanics.made_up"
    assert rules(p.l1_problems(audit)) == ["unknown_model"]


def test_a_model_fed_the_wrong_inputs_is_refused() -> None:
    audit = good_audit()
    audit["readouts"][0]["chain"]["inputs"] = {"force": audit["readouts"][0]["chain"]["inputs"]["load"]}
    assert rules(p.l1_problems(audit)) == ["ungrounded_readout"]


def test_a_model_fed_a_free_observable_is_ungrounded() -> None:
    audit = good_audit()
    audit["readouts"][0]["chain"]["inputs"]["load"] = {"kind": "free"}
    assert rules(p.l1_problems(audit)) == ["ungrounded_readout"]


def test_overwritten_readout_text_is_readout_mismatch() -> None:
    audit = good_audit()
    audit["readouts"][0]["displayed"] = "0.123 m"
    assert rules(p.l1_problems(audit)) == ["readout_mismatch"]


def test_an_edited_kit_element_and_an_unowned_number_are_refused() -> None:
    audit = good_audit()
    audit["ownedMismatches"] = [{"tag": "div", "expected": "Hang a load.", "actual": "The extension is 0.9 m"}]
    audit["unownedNumbers"] = [{"text": "0.04 m", "parent": "p"}]
    assert set(rules(p.l1_problems(audit))) == {"owned_changed", "unowned_number"}


def test_a_displayed_number_that_differs_from_the_reference_is_numeric_mismatch() -> None:
    """The Kit is trusted to format; L3 recomputes the value independently, so a wrong value is caught even if display equals expected."""
    audit = good_audit()
    audit["readouts"][0].update(value=0.08, displayed="0.080 m", expected="0.080 m")
    assert p.l1_problems(audit) == []  # text and value agree with each other...
    problems, _ = p.l3_problems(audit)
    assert set(rules(problems)) == {"numeric_mismatch"}  # ...but not with physics


def test_a_non_numeric_display_is_non_finite() -> None:
    audit = good_audit()
    audit["readouts"][0].update(displayed="NaN m", expected="NaN m")
    problems, _ = p.l3_problems(audit)
    assert rules(problems) == ["non_finite_readout"]


def test_the_reference_is_evaluated_at_the_controls_reported_in_the_audit() -> None:
    audit = good_audit()
    audit["controls"][0]["value"] = 10
    audit["readouts"][0].update(value=0.2, displayed="0.200 m", expected="0.200 m")
    problems, compared = p.l3_problems(audit)
    assert problems == [] and compared == 1


def test_display_rounding_is_tolerated_but_not_more() -> None:
    audit = good_audit()
    audit["controls"][0]["value"] = 3.3333  # 3.3333 / 50 = 0.066666
    audit["readouts"][0].update(value=3.3333 / 50, displayed="0.067 m", expected="0.067 m")
    assert p.l3_problems(audit)[0] == []
    audit["readouts"][0].update(displayed="0.068 m", expected="0.068 m")
    assert rules(p.l3_problems(audit)[0]) == ["numeric_mismatch"]


# ── copy numbers ────────────────────────────────────────────────────────────────────────────────────────────────────────


def with_copy(*texts: str) -> dict:
    audit = good_audit()
    audit["copy"] = [{"text": t, "numbers": []} for t in texts]
    return audit


@pytest.mark.parametrize(
    "text",
    [
        "The spring constant is 50 N/m.",  # a model parameter
        "Choose a load from 0 to 10 N.",  # a control range
        "Start at 2 N.",  # a control default
        "Step 2: move the slider.",  # a step marker
        "1. Hang the load.",  # a list marker
        "KSSM Physics Form 5.",  # context word
        "Water is H2O and the circuit has R1 and R2.",  # identifiers
    ],
)
def test_backed_or_contextual_numbers_in_copy_are_allowed(text: str) -> None:
    assert p.copy_number_problems(with_copy(text)) == []


@pytest.mark.parametrize(
    "text", ["The extension is 0.04 m.", "A 13 N load stretches it by 12 cm.", "It stretches 12 times as far."]
)
def test_an_unbacked_number_in_copy_is_refused(text: str) -> None:
    found = rules(p.copy_number_problems(with_copy(text)))
    assert found and set(found) == {"unbacked_copy_number"}


def test_KNOWN_LIMIT_backing_compares_values_not_meaning() -> None:
    """A sentence may state "3 times as far" when 3 is also a grid position of some control: the check sees a backed value, not what the
    sentence claims about it. The same holds for any number that happens to equal a parameter. The L6 report lists this under the
    classes of bug that are NOT tried; the real guard is that the page has little room for free copy and a person reviews it."""
    assert p.copy_number_problems(with_copy("It stretches 3 times as far.")) == []


# ── plan ────────────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_a_changed_parameter_or_an_unplanned_model_is_a_plan_mismatch() -> None:
    audit = good_audit()
    changed = p.plan_problems(audit, [{"id": "mechanics.hookes", "params": {"k": 25}}])
    assert rules(changed) == ["plan_mismatch"]
    assert "'k': 25.0" in changed[0].reason and "'k': 50.0" in changed[0].reason  # both sides are named
    assert rules(p.plan_problems(audit, [])) == ["plan_mismatch"]
    assert p.plan_problems(audit, None) == []


def test_models_in_lists_each_distinct_model_once() -> None:
    chain = {"kind": "convert", "inputs": {"x": good_audit()["readouts"][0]["chain"]}}
    assert p.models_in(chain) == [("mechanics.hookes", (("k", 50.0),))]


# ── references ──────────────────────────────────────────────────────────────────────────────────────────────────────────

WORKED = [
    ("mechanics.hookes", {"k": 50}, {"load": 10}, 0.2),
    ("mechanics.hookes", {"k": 50}, {"load": 2}, 0.04),
    ("mechanics.hookes", {"k": 20}, {"load": 4}, 0.2),
    ("electricity.ohm", {}, {"voltage": 12, "resistance": 4}, 3.0),
    ("electricity.ohm", {}, {"voltage": 6, "resistance": 12}, 0.5),
    ("electricity.ohm", {}, {"voltage": 230, "resistance": 46}, 5.0),
    ("fluids.pressure_depth", {"density": 1000, "g": 10}, {"depth": 2}, 20000.0),
    ("fluids.pressure_depth", {"density": 1000, "g": 9.81}, {"depth": 10}, 98100.0),
    ("fluids.pressure_depth", {"density": 13600, "g": 10}, {"depth": 0.5}, 68000.0),
    ("biology.magnification", {}, {"image": 50, "actual": 0.5}, 100.0),
    ("biology.magnification", {}, {"image": 30, "actual": 0.02}, 1500.0),
    ("biology.sa_to_v_cube", {}, {"side": 2}, 3.0),
    ("biology.sa_to_v_cube", {}, {"side": 0.5}, 12.0),
    ("biology.photosynthesis_net", {"pmax": 10, "k": 4, "resp": 2}, {"light": 4}, 3.0),
    ("biology.photosynthesis_net", {"pmax": 10, "k": 4, "resp": 2}, {"light": 1}, 0.0),
    ("biology.photosynthesis_net", {"pmax": 10, "k": 4, "resp": 2}, {"light": 0}, -2.0),
    ("chemistry.moles_from_mass", {"molar_mass": 18}, {"mass": 36}, 2.0),
    ("chemistry.moles_from_mass", {"molar_mass": 58.5}, {"mass": 5.85}, 0.1),
    ("chemistry.titration_concentration", {"ma": 0.1, "acid_coeff": 1, "base_coeff": 1}, {"va": 25, "vb": 20}, 0.125),
    ("chemistry.titration_concentration", {"ma": 0.1, "acid_coeff": 1, "base_coeff": 2}, {"va": 25, "vb": 20}, 0.25),
    ("chemistry.titration_concentration", {"ma": 0.2, "acid_coeff": 2, "base_coeff": 1}, {"va": 10, "vb": 40}, 0.025),
    ("chemistry.dilution", {"m1": 2, "v1": 25}, {"v2": 100}, 0.5),
    ("chemistry.dilution", {"m1": 0.1, "v1": 100}, {"v2": 250}, 0.04),
    ("chemistry.heat_energy", {"mass": 100, "c": 4.2}, {"delta_t": 5}, 2100.0),
    ("chemistry.heat_energy", {"mass": 50, "c": 4.2}, {"delta_t": 6.5}, 1365.0),
    ("chemistry.average_rate", {}, {"volume": 24, "time": 60}, 0.4),
    ("chemistry.average_rate", {}, {"volume": 36, "time": 12}, 3.0),
    ("physics.wave_speed", {}, {"frequency": 50, "wavelength": 0.4}, 20.0),
    ("physics.wave_speed", {}, {"frequency": 100, "wavelength": 3.4}, 340.0),
    ("physics.newton_second", {}, {"force": 10, "mass": 2}, 5.0),
    ("physics.newton_second", {}, {"force": 15, "mass": 0.5}, 30.0),
    ("biology.cardiac_output", {}, {"heart_rate": 72, "stroke_volume": 70}, 5.04),
    ("biology.cardiac_output", {}, {"heart_rate": 150, "stroke_volume": 120}, 18.0),
    ("biology.percent_change_mass", {"initial_mass": 10}, {"final_mass": 12}, 20.0),
    ("biology.percent_change_mass", {"initial_mass": 10}, {"final_mass": 8}, -20.0),
    ("chemistry.ph_from_h", {}, {"h_conc": 0.001}, 3.0),
    ("chemistry.ph_from_h", {}, {"h_conc": 1e-7}, 7.0),
    ("chemistry.gas_volume", {"molar_volume": 24}, {"moles": 2}, 48.0),
    ("chemistry.gas_volume", {"molar_volume": 22.4}, {"moles": 0.5}, 11.2),
]


@pytest.mark.parametrize(("model", "params", "inputs", "expected"), WORKED)
def test_references_match_the_values_worked_out_by_hand(
    model: str, params: dict, inputs: dict, expected: float
) -> None:
    assert evaluate_model(model, params, inputs) == pytest.approx(expected, rel=1e-12, abs=1e-12)


@pytest.mark.parametrize(
    ("model", "params", "inputs"),
    [
        ("mechanics.hookes", {"k": 0}, {"load": 1}),
        ("mechanics.hookes", {"k": 10}, {"load": -1}),
        ("mechanics.hookes", {"k": float("nan")}, {"load": 1}),
        ("electricity.ohm", {}, {"voltage": 1, "resistance": 0}),
        ("electricity.ohm", {}, {"voltage": -1, "resistance": 1}),
        ("fluids.pressure_depth", {"density": 0, "g": 10}, {"depth": 1}),
        ("fluids.pressure_depth", {"density": 1000, "g": 10}, {"depth": -1}),
        ("biology.magnification", {}, {"image": 1, "actual": 0}),
        ("biology.magnification", {}, {"image": -1, "actual": 1}),
        ("biology.sa_to_v_cube", {}, {"side": 0}),
        ("biology.photosynthesis_net", {"pmax": 10, "k": 0, "resp": 2}, {"light": 1}),
        ("biology.photosynthesis_net", {"pmax": 10, "k": 4, "resp": -1}, {"light": 1}),
        ("chemistry.moles_from_mass", {"molar_mass": 0}, {"mass": 1}),
        ("physics.wave_speed", {}, {"frequency": 0, "wavelength": 1}),
        ("physics.newton_second", {}, {"force": 1, "mass": 0}),
        ("biology.cardiac_output", {}, {"heart_rate": -1, "stroke_volume": 70}),
        ("biology.percent_change_mass", {"initial_mass": 0}, {"final_mass": 1}),
        ("chemistry.ph_from_h", {}, {"h_conc": 0}),
        ("chemistry.gas_volume", {"molar_volume": 0}, {"moles": 1}),
        ("chemistry.titration_concentration", {"ma": 0.1, "acid_coeff": 0, "base_coeff": 1}, {"va": 25, "vb": 20}),
        ("chemistry.titration_concentration", {"ma": 0.1, "acid_coeff": 1, "base_coeff": 1}, {"va": 25, "vb": 0}),
        ("chemistry.dilution", {"m1": 1, "v1": 10}, {"v2": 0}),
        ("chemistry.heat_energy", {"mass": 0, "c": 4.2}, {"delta_t": 1}),
        ("chemistry.heat_energy", {"mass": 100, "c": 4.2}, {"delta_t": -1}),
        ("chemistry.average_rate", {}, {"volume": 1, "time": 0}),
    ],
)
def test_references_refuse_values_outside_the_domain(model: str, params: dict, inputs: dict) -> None:
    with pytest.raises(ValueError):
        evaluate_model(model, params, inputs)


def test_references_refuse_missing_or_extra_arguments() -> None:
    with pytest.raises(ValueError):
        evaluate_model("mechanics.hookes", {}, {"load": 1})
    with pytest.raises(ValueError):
        evaluate_model("electricity.ohm", {"k": 1}, {"voltage": 1, "resistance": 1})
    with pytest.raises(KeyError):
        evaluate_model("nope.nope", {}, {})


def test_references_obey_the_same_properties_the_kit_registration_requires() -> None:
    # Second routes to the same answer: elastic energy E = F^2 / 2k equals F x / 2; electrical power V^2 / R equals V I.
    for load, k in [(2, 50), (10, 50), (4, 20)]:
        x = evaluate_model("mechanics.hookes", {"k": k}, {"load": load})
        assert load**2 / (2 * k) == pytest.approx(load * x / 2, rel=1e-12)
    for v, r in [(12, 4), (6, 12)]:
        i = evaluate_model("electricity.ohm", {}, {"voltage": v, "resistance": r})
        assert v**2 / r == pytest.approx(v * i, rel=1e-12)
    # Doubling the depth doubles the pressure; doubling the density doubles it too.
    base = evaluate_model("fluids.pressure_depth", {"density": 1000, "g": 10}, {"depth": 3})
    assert evaluate_model("fluids.pressure_depth", {"density": 1000, "g": 10}, {"depth": 6}) == pytest.approx(2 * base)
    assert evaluate_model("fluids.pressure_depth", {"density": 2000, "g": 10}, {"depth": 3}) == pytest.approx(2 * base)


def test_every_science_model_in_the_kit_manifest_has_a_reference_and_the_reverse(kit_dist: Path) -> None:
    manifest = json.loads((kit_dist / "0.1.0" / "manifest.json").read_text(encoding="utf-8"))
    kit_models = {c["modelId"] for c in manifest["components"] if c["kind"] == "science"}
    assert kit_models == set(REFERENCES)
    for c in manifest["components"]:
        if c["kind"] == "science":
            assert c["citation"].startswith("UNVERIFIED")


def test_the_audit_helpers_do_not_mutate_their_input() -> None:
    audit = good_audit()
    snapshot = copy.deepcopy(audit)
    p.l1_problems(audit)
    p.l3_problems(audit)
    p.plan_problems(audit, [])
    assert audit == snapshot


def convert_audit(factor: float, source: str = "mm", target: str = "m") -> dict:
    audit = good_audit()
    audit["readouts"][0]["chain"] = {
        "kind": "convert",
        "from": source,
        "to": target,
        "factor": factor,
        "inputs": {"x": {"kind": "control", "id": "load", "min": 0, "max": 10, "grid": 10, "default": 2}},
    }
    return audit


def test_a_conversion_must_use_the_independent_unit_factor() -> None:
    assert rules(p.l1_problems(convert_audit(0.001))) == []
    assert "bad_unit_factor" in rules(p.l1_problems(convert_audit(0.01)))  # the Kit claims the wrong factor
    assert "bad_unit_factor" in rules(p.l1_problems(convert_audit(1.0, "mm", "kg")))  # across dimensions
    assert "bad_unit_factor" in rules(p.l1_problems(convert_audit(1.0, "furlong", "m")))  # unknown unit


def test_the_kit_unit_table_and_the_independent_one_agree() -> None:
    """convert.ts and references.UNIT_SI are written separately; this pins that they say the same thing."""
    import re

    from api.verify.references import UNIT_SI

    source = (Path(__file__).resolve().parents[2] / "packages/kit/src/convert.ts").read_text(encoding="utf-8")
    kit = {
        m.group(1): (m.group(2), float(m.group(3)))
        for m in re.finditer(r'(\w+): \{ dim: "(\w+)", toSI: ([0-9.eE+-]+) \}', source)
    }
    assert kit == UNIT_SI


def test_a_number_in_an_attribute_the_kit_did_not_set_is_refused() -> None:
    audit = good_audit()
    audit["unownedAttributeNumbers"] = [{"element": "p", "attribute": "aria-label", "value": "0.04 m"}]
    assert rules(p.l1_problems(audit)) == ["unowned_attribute_number"]


def test_a_shadow_root_is_refused_because_it_cannot_be_audited() -> None:
    audit = good_audit()
    audit["shadowRoots"] = 1
    assert rules(p.l1_problems(audit)) == ["shadow_root"]


def test_a_readout_unit_must_match_the_unit_of_what_it_shows() -> None:
    audit = good_audit()
    audit["readouts"][0]["unit"] = "cm"
    audit["readouts"][0]["displayed"] = audit["readouts"][0]["expected"] = (
        "0.040 cm"  # the Kit would format it this way
    )
    assert "wrong_unit" in rules(p.l1_problems(audit))
    # a conversion changes the unit the readout must carry
    ok = convert_audit(0.001)
    ok["readouts"][0]["unit"] = "m"
    ok["readouts"][0]["displayed"] = ok["readouts"][0]["expected"] = "0.040 m"
    assert "wrong_unit" not in rules(p.l1_problems(ok))
    ok["readouts"][0]["unit"] = "mm"
    ok["readouts"][0]["displayed"] = ok["readouts"][0]["expected"] = "0.040 mm"
    assert "wrong_unit" in rules(p.l1_problems(ok))


def series_audit(points: list[list[float]] | None = None, value: float = 0.04) -> dict:
    audit = good_audit()
    audit["series"] = [
        {
            "kind": "graph",
            "title": "t",
            "label": "Extension",
            "unit": "m",
            "digits": 3,
            "value": value,
            "xControl": "load",
            "points": points if points is not None else [[0, 0], [5, 0.1], [10, 0.2]],
            "chain": audit["readouts"][0]["chain"],
        }
    ]
    return audit


def test_a_graph_curve_is_rederived_point_by_point_from_the_reference() -> None:
    audit = series_audit()
    assert p.l1_problems(audit) == []
    problems, compared = p.l3_problems(audit)
    assert problems == [] and compared == 1 + 1 + 3  # the readout, the series value, three curve points
    bad = p.l3_problems(series_audit(points=[[0, 0], [5, 0.11], [10, 0.2]]))[0]
    assert rules(bad) == ["numeric_mismatch"] and "load=5" in bad[0].reason
    assert rules(p.l3_problems(series_audit(value=0.05))[0]) == ["numeric_mismatch"]


def test_a_series_is_held_to_the_same_chain_and_unit_rules_as_a_readout() -> None:
    audit = series_audit()
    audit["series"][0]["chain"] = {"kind": "free"}
    assert rules(p.l1_problems(audit)) == ["ungrounded_readout"]
    audit = series_audit()
    audit["series"][0]["unit"] = "mm"
    assert rules(p.l1_problems(audit)) == ["wrong_unit"]


def test_a_model_used_only_by_a_graph_still_counts_against_the_plan() -> None:
    audit = series_audit()
    audit["readouts"] = []
    assert p.plan_problems(audit, [{"id": "mechanics.hookes", "params": {"k": 50}}]) == []
    assert rules(p.plan_problems(audit, [])) == ["plan_mismatch"]


def test_forged_actions_are_refused() -> None:
    audit = good_audit()
    audit["forgedActions"] = 1
    assert rules(p.l1_problems(audit)) == ["forged_action"]


def test_second_routes_agree_for_the_new_models() -> None:
    """Independent identities, not the same formula run twice."""
    # Moles: n = m / M, so m = n M.
    n = evaluate_model("chemistry.moles_from_mass", {"molar_mass": 40}, {"mass": 10})
    assert n * 40 == pytest.approx(10, rel=1e-12)
    # Titration with equal coefficients: the moles of acid and of base at the end point are equal.
    mb = evaluate_model(
        "chemistry.titration_concentration", {"ma": 0.1, "acid_coeff": 1, "base_coeff": 1}, {"va": 25, "vb": 20}
    )
    assert mb * 20 == pytest.approx(0.1 * 25, rel=1e-12)
    # Dilution keeps the amount of solute: M1 V1 = M2 V2.
    m2 = evaluate_model("chemistry.dilution", {"m1": 2, "v1": 25}, {"v2": 100})
    assert m2 * 100 == pytest.approx(2 * 25, rel=1e-12)
    # Heat: doubling the mass or the temperature change doubles Q.
    q = evaluate_model("chemistry.heat_energy", {"mass": 100, "c": 4.2}, {"delta_t": 5})
    assert evaluate_model("chemistry.heat_energy", {"mass": 200, "c": 4.2}, {"delta_t": 5}) == pytest.approx(2 * q)
    # SA:V of a cube: area 6 s^2 over volume s^3 gives 6 / s.
    for s in (0.5, 2, 3):
        assert evaluate_model("biology.sa_to_v_cube", {}, {"side": s}) == pytest.approx(6 * s**2 / s**3)
    # The compensation point: net uptake is zero at I* = resp k / (pmax - resp).
    params: dict[str, float] = {"pmax": 10, "k": 4, "resp": 2}
    star = 2 * 4 / (10 - 2)
    assert evaluate_model("biology.photosynthesis_net", params, {"light": star}) == pytest.approx(0, abs=1e-12)
    # Magnification of a drawing: image = magnification x actual.
    x = evaluate_model("biology.magnification", {}, {"image": 80, "actual": 0.16})
    assert x * 0.16 == pytest.approx(80, rel=1e-12)
