// biology.food_energy_value: the energy value of a food from burning a sample under water, (water mass x 4.2 J/g degC x rise in water temperature) / (food mass x 1000), in
// kJ per gram (Balanced Diet: energy value of food). The 4.2 is the specific heat capacity of water the textbook gives. Masses are in grams, the rise in degrees Celsius.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.food_energy_value",
  exportName: "foodEnergyValue",
  inputs: { temperature_rise: { unit: "°C", min: 0 }, food_mass: { unit: "g", min: 0, exclusive: true } },
  params: { water_mass: { unit: "g", min: 0, exclusive: true } },
  output: { unit: "kJ/g" },
  fn: ({ temperature_rise, food_mass, water_mass }) => ((water_mass as number) * 4.2 * (temperature_rise as number)) / ((food_mass as number) * 1000),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from the textbook's formula. Water is 1 g per ml, as the experiment assumes (20 ml of water is 20 g).
  reference: [
    { args: { temperature_rise: 25, food_mass: 0.8, water_mass: 20 }, expected: 2.625, tolerance: 1e-9, derivation: "20 x 4.2 x 25 / (0.8 x 1000) = 2 100 / 800 = 2.625 kJ/g" },
    { args: { temperature_rise: 40, food_mass: 1, water_mass: 20 }, expected: 3.36, tolerance: 1e-9, derivation: "20 x 4.2 x 40 / 1000 = 3.36 kJ/g" },
    { args: { temperature_rise: 0, food_mass: 1, water_mass: 20 }, expected: 0, tolerance: 1e-12, derivation: "no rise in temperature means no energy measured" },
    { args: { temperature_rise: 10, food_mass: 2, water_mass: 50 }, expected: 1.05, tolerance: 1e-9, derivation: "50 x 4.2 x 10 / (2 x 1000) = 1.05 kJ/g" },
    { args: { temperature_rise: 60, food_mass: 0.5, water_mass: 20 }, expected: 10.08, tolerance: 1e-9, derivation: "20 x 4.2 x 60 / (0.5 x 1000) = 10.08 kJ/g" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "temperature_rise" },
    { kind: "decreasing", arg: "food_mass" },
    { kind: "increasing", arg: "water_mass" },
    { kind: "homogeneous", arg: "temperature_rise", degree: 1 },
    { kind: "homogeneous", arg: "food_mass", degree: -1 },
    { kind: "homogeneous", arg: "water_mass", degree: 1 },
  ],
  grid: { temperature_rise: [5, 10, 25, 40, 60], food_mass: [0.5, 0.8, 1, 2], water_mass: [20, 50] },
};

export function foodEnergyValue(options: { temperature_rise: Observable<number>; food_mass: Observable<number>; water_mass: number }): Observable<number> {
  return model(spec, { water_mass: options.water_mass }, { temperature_rise: options.temperature_rise, food_mass: options.food_mass });
}
