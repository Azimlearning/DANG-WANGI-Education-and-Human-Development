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
        "foreign": [],
        "shadowRoots": 0,
        "widgets": [],
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


@pytest.mark.parametrize(
    "text",
    [
        "The extension is .99 m.",  # a leading-dot decimal used to be invisible to the check
        "It stretches by -.5 m.",
        "The force is about 7e1 N.",  # the exponent form means 50, not 5
        "A load of 1E-2 N.",
    ],
)
def test_a_number_written_with_a_leading_dot_or_an_exponent_is_seen_and_refused_when_unbacked(text: str) -> None:
    assert set(rules(p.copy_number_problems(with_copy(text)))) == {"unbacked_copy_number"}


@pytest.mark.parametrize(
    "text",
    [
        "Hold the load at x.5 on the ruler.",  # a name followed by .5 is an identifier, not a quantity
        "See version 1.2.3 of the figure.",  # 1.2 is unbacked, but the trailing .3 is not a second number (it must not add one)
    ],
)
def test_identifier_like_text_does_not_become_extra_numbers(text: str) -> None:
    got = [m.group() for m in p.COPY_NUMBER.finditer(text)]
    assert ".5" not in got and ".3" not in got and "3" not in got


def test_the_number_pattern_reads_each_form_as_the_value_a_person_means() -> None:
    values = lambda t: [float(m.group()) for m in p.COPY_NUMBER.finditer(t)]  # noqa: E731
    assert values("0.04 m and .99 m and -.5 N") == [0.04, 0.99, -0.5]
    assert values("5e1 N then 1E-2 m") == [50.0, 0.01]
    assert values("R1 and H2O and x.5") == []


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
    ("physics.weight", {}, {"mass": 1, "gravity": 9.81}, 9.81),
    ("physics.weight", {}, {"mass": 5, "gravity": 3.7}, 18.5),
    ("physics.weight", {}, {"mass": 0, "gravity": 24.79}, 0.0),
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
    # Worked by hand. Refraction: sin 45 = sqrt2/2 and n = sqrt2 give sin r = 1/2, so r = 30; likewise sin 60 = sqrt3/2 with n = sqrt3.
    ("physics.refraction_angle", {}, {"incidence_angle": 45, "refractive_index": 2**0.5}, 30.0),
    ("physics.refraction_angle", {}, {"incidence_angle": 60, "refractive_index": 3**0.5}, 30.0),
    ("physics.refraction_angle", {}, {"incidence_angle": 30, "refractive_index": 1}, 30.0),
    ("physics.refraction_angle", {}, {"incidence_angle": 0, "refractive_index": 1.5}, 0.0),
    # Critical angle: sin c = 1/n. n = 1 gives 90, n = 2 gives 30, n = sqrt2 gives 45.
    ("physics.critical_angle", {}, {"refractive_index": 1}, 90.0),
    ("physics.critical_angle", {}, {"refractive_index": 2}, 30.0),
    ("physics.critical_angle", {}, {"refractive_index": 2**0.5}, 45.0),
    # Specific heat: Q = m c dT.
    ("physics.specific_heat", {"specific_heat": 4200}, {"mass": 1, "temperature_change": 1}, 4200.0),
    ("physics.specific_heat", {"specific_heat": 4200}, {"mass": 2, "temperature_change": 50}, 420000.0),
    ("physics.specific_heat", {"specific_heat": 900}, {"mass": 0.5, "temperature_change": 40}, 18000.0),
    # Transformer: Vs = Vp Ns / Np. The first is the textbook's worked example.
    ("physics.transformer_voltage", {"primary_voltage": 240}, {"primary_turns": 800, "secondary_turns": 60}, 18.0),
    ("physics.transformer_voltage", {"primary_voltage": 12}, {"primary_turns": 100, "secondary_turns": 500}, 60.0),
    # Half-life: N = N0 / 2^(t / T). The first is the textbook's worked example: five half-lives of 6 minutes leave 480 / 32 = 15.
    ("physics.half_life_decay", {"half_life": 6, "initial": 480}, {"time": 30}, 15.0),
    ("physics.half_life_decay", {"half_life": 10, "initial": 100}, {"time": 20}, 25.0),
    # Relative atomic mass: the first is the textbook's chlorine example.
    ("chemistry.relative_atomic_mass", {"mass_1": 35, "mass_2": 37}, {"abundance_1": 75}, 35.5),
    ("chemistry.relative_atomic_mass", {"mass_1": 63, "mass_2": 65}, {"abundance_1": 70}, 63.6),
    ("chemistry.relative_atomic_mass", {"mass_1": 35, "mass_2": 37}, {"abundance_1": 100}, 35.0),
    # Energy value of a food: water mass x 4.2 x rise / (food mass x 1000).
    ("biology.food_energy_value", {"water_mass": 20}, {"temperature_rise": 25, "food_mass": 0.8}, 2.625),
    ("biology.food_energy_value", {"water_mass": 50}, {"temperature_rise": 10, "food_mass": 2}, 1.05),
    # Boyle's law: the first is the textbook's syringe example.
    ("physics.boyle_law", {"initial_pressure": 108, "initial_volume": 60}, {"final_volume": 48}, 135.0),
    ("physics.boyle_law", {"initial_pressure": 100, "initial_volume": 50}, {"final_volume": 25}, 200.0),
    # Two resistors in parallel: the first is the textbook's 4 ohm and 12 ohm example.
    ("physics.parallel_resistance", {}, {"resistance_1": 4, "resistance_2": 12}, 3.0),
    ("physics.parallel_resistance", {}, {"resistance_1": 6, "resistance_2": 6}, 3.0),
    # Buoyant force: F = rho V g.
    ("physics.buoyant_force", {"density": 1000, "g": 10}, {"volume": 0.002}, 20.0),
    ("physics.buoyant_force", {"density": 1000, "g": 9.81}, {"volume": 0.001}, 9.81),
    # Cell voltage: the first is the textbook's Daniell cell, +1.10 V.
    ("chemistry.cell_voltage", {"anode_potential": -0.76}, {"cathode_potential": 0.34}, 1.1),
    ("chemistry.cell_voltage", {"anode_potential": 0.34}, {"cathode_potential": 0.8}, 0.46),
    # Population density by quadrat sampling.
    ("biology.population_density", {"quadrats": 10, "quadrat_area": 1}, {"total_count": 45}, 4.5),
    ("biology.population_density", {"quadrats": 5, "quadrat_area": 0.25}, {"total_count": 20}, 16.0),
    # Electrical energy: the first is the textbook's lamp, 252 J.
    ("physics.electrical_energy", {"voltage": 6}, {"current": 0.7, "time": 60}, 252.0),
    ("physics.electrical_energy", {"voltage": 12}, {"current": 1.5, "time": 120}, 2160.0),
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
        ("physics.refraction_angle", {}, {"incidence_angle": 90, "refractive_index": 1.5}),  # the ceiling is exclusive
        ("physics.refraction_angle", {}, {"incidence_angle": 120, "refractive_index": 1.5}),
        ("physics.refraction_angle", {}, {"incidence_angle": -1, "refractive_index": 1.5}),
        ("physics.refraction_angle", {}, {"incidence_angle": 30, "refractive_index": 0.99}),
        ("physics.critical_angle", {}, {"refractive_index": 0.99}),
        ("physics.specific_heat", {"specific_heat": 4200}, {"mass": 0, "temperature_change": 1}),
        ("physics.specific_heat", {"specific_heat": 4200}, {"mass": 1, "temperature_change": -1}),
        ("physics.specific_heat", {"specific_heat": 0}, {"mass": 1, "temperature_change": 1}),
        ("physics.transformer_voltage", {"primary_voltage": 240}, {"primary_turns": 0, "secondary_turns": 60}),
        ("physics.transformer_voltage", {"primary_voltage": 240}, {"primary_turns": 800, "secondary_turns": 0}),
        ("physics.transformer_voltage", {"primary_voltage": 0}, {"primary_turns": 800, "secondary_turns": 60}),
        ("physics.half_life_decay", {"half_life": 0, "initial": 100}, {"time": 1}),
        ("physics.half_life_decay", {"half_life": 10, "initial": 0}, {"time": 1}),
        ("physics.half_life_decay", {"half_life": 10, "initial": 100}, {"time": -1}),
        ("chemistry.relative_atomic_mass", {"mass_1": 35, "mass_2": 37}, {"abundance_1": 101}),
        ("chemistry.relative_atomic_mass", {"mass_1": 35, "mass_2": 37}, {"abundance_1": -1}),
        ("chemistry.relative_atomic_mass", {"mass_1": 0, "mass_2": 37}, {"abundance_1": 50}),
        ("biology.food_energy_value", {"water_mass": 20}, {"temperature_rise": -1, "food_mass": 1}),
        ("biology.food_energy_value", {"water_mass": 20}, {"temperature_rise": 10, "food_mass": 0}),
        ("biology.food_energy_value", {"water_mass": 0}, {"temperature_rise": 10, "food_mass": 1}),
        ("physics.boyle_law", {"initial_pressure": 108, "initial_volume": 60}, {"final_volume": 0}),
        ("physics.boyle_law", {"initial_pressure": 0, "initial_volume": 60}, {"final_volume": 48}),
        ("physics.boyle_law", {"initial_pressure": 108, "initial_volume": 0}, {"final_volume": 48}),
        ("physics.parallel_resistance", {}, {"resistance_1": 0, "resistance_2": 12}),
        ("physics.parallel_resistance", {}, {"resistance_1": 4, "resistance_2": -1}),
        ("physics.buoyant_force", {"density": 1000, "g": 10}, {"volume": -0.001}),
        ("physics.buoyant_force", {"density": 0, "g": 10}, {"volume": 0.002}),
        ("physics.buoyant_force", {"density": 1000, "g": 0}, {"volume": 0.002}),
        ("chemistry.cell_voltage", {"anode_potential": -0.76}, {"cathode_potential": 3.5}),
        ("chemistry.cell_voltage", {"anode_potential": -3.5}, {"cathode_potential": 0.34}),
        ("biology.population_density", {"quadrats": 10, "quadrat_area": 1}, {"total_count": -1}),
        ("biology.population_density", {"quadrats": 0, "quadrat_area": 1}, {"total_count": 45}),
        ("biology.population_density", {"quadrats": 10, "quadrat_area": 0}, {"total_count": 45}),
        ("physics.electrical_energy", {"voltage": 6}, {"current": -0.1, "time": 60}),
        ("physics.electrical_energy", {"voltage": 6}, {"current": 0.7, "time": -1}),
        ("physics.electrical_energy", {"voltage": 0}, {"current": 0.7, "time": 60}),
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


def convert_audit_from_a_control_in(unit: str, factor: float, source: str, target: str) -> dict:
    audit = convert_audit(factor, source, target)
    audit["controls"][0]["unit"] = unit
    audit["readouts"][0]["unit"] = target
    return audit


def test_a_conversion_must_use_the_independent_unit_factor() -> None:
    # The control is declared in the conversion's starting unit, so only the factor and the dimensions are under test here.
    def l1(factor: float, source: str = "mm", target: str = "m") -> list[str]:
        return rules(p.l1_problems(convert_audit_from_a_control_in(source, factor, source, target)))

    assert l1(0.001) == []
    assert "bad_unit_factor" in l1(0.01)  # the Kit claims the wrong factor
    assert "bad_unit_factor" in l1(1.0, "mm", "kg")  # across dimensions
    assert "bad_unit_factor" in l1(1.0, "furlong", "m")  # unknown unit


def test_a_conversion_must_start_from_the_unit_its_source_is_really_in() -> None:
    """The conversion's factor is right and its label is right, so every other check agrees; only the source's unit exposes it."""
    # A control in newtons cannot be converted "from mm".
    assert "wrong_conversion_source" in rules(p.l1_problems(convert_audit(0.001)))
    # The same conversion from a control that IS in mm is fine.
    assert rules(p.l1_problems(convert_audit_from_a_control_in("mm", 0.001, "mm", "m"))) == []
    # A model's output is in metres: converting it "from mm" shows a value 1000 times too small, labelled metres.
    audit = good_audit()
    audit["readouts"][0]["chain"] = {
        "kind": "convert",
        "from": "mm",
        "to": "m",
        "factor": 0.001,
        "inputs": {"x": good_audit()["readouts"][0]["chain"]},
    }
    found = p.l1_problems(audit)
    assert "wrong_conversion_source" in rules(found)
    assert any("'m'" in f.reason and "'mm'" in f.reason for f in found)
    # Converting that same output from its real unit, m to mm, and labelling it mm, is accepted.
    audit["readouts"][0]["chain"].update({"from": "m", "to": "mm", "factor": 1000.0})
    audit["readouts"][0]["unit"] = "mm"
    assert "wrong_conversion_source" not in rules(p.l1_problems(audit))
    # A source whose unit nothing declares fails closed rather than passing.
    audit["controls"][0]["unit"] = ""
    audit["readouts"][0]["chain"] = {
        "kind": "convert",
        "from": "mm",
        "to": "m",
        "factor": 0.001,
        "inputs": {"x": {"kind": "control", "id": "ghost", "min": 0, "max": 1, "grid": 2, "default": 0}},
    }
    assert "wrong_conversion_source" in rules(p.l1_problems(audit))


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


def test_planet_gravity_agrees_with_the_published_surface_gravity_of_each_planet() -> None:
    # Published values of G M / R^2 at the equator (worked by hand from the fact sheet, not by running the reference): within 1 percent.
    published = {1: 3.70, 2: 8.87, 3: 9.80, 4: 3.71, 5: 24.79, 6: 10.44, 7: 8.87, 8: 11.15}
    for planet, g in published.items():
        assert evaluate_model("physics.planet_gravity", {}, {"planet": planet}) == pytest.approx(g, rel=0.01)
    # Jupiter pulls hardest and Mercury and Mars least; Earth is between Venus and Saturn.
    gs = {p: evaluate_model("physics.planet_gravity", {}, {"planet": p}) for p in range(1, 9)}
    assert max(gs, key=gs.__getitem__) == 5
    assert gs[3] > gs[2]
    with pytest.raises(ValueError):
        evaluate_model("physics.planet_gravity", {}, {"planet": 9})
    with pytest.raises(ValueError):
        evaluate_model("physics.planet_gravity", {}, {"planet": 0})
