// physics.specific_heat: the heat needed to change the temperature of a mass of a substance, Q = m c (delta theta) (Heat: specific heat capacity). Mass in kilograms, specific
// heat capacity c in joules per kilogram per degree Celsius, temperature change in degrees Celsius (a rise; the quantity of heat comes out in joules). The SI units of the
// textbook, unlike chemistry.heat_energy, which works in grams and joules per gram.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.specific_heat",
  exportName: "specificHeat",
  inputs: { mass: { unit: "kg", min: 0, exclusive: true }, temperature_change: { unit: "°C", min: 0 } },
  params: { specific_heat: { unit: "J/kg°C", min: 0, exclusive: true } },
  output: { unit: "J" },
  fn: ({ mass, temperature_change, specific_heat }) => (mass as number) * (specific_heat as number) * (temperature_change as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from Q = m c (delta theta).
  reference: [
    { args: { mass: 1, temperature_change: 1, specific_heat: 4200 }, expected: 4200, tolerance: 1e-9, derivation: "1 kg of water by 1 degree needs c = 4 200 J" },
    { args: { mass: 2, temperature_change: 50, specific_heat: 4200 }, expected: 420000, tolerance: 1e-6, derivation: "2 x 4 200 x 50 = 420 000 J" },
    { args: { mass: 0.5, temperature_change: 40, specific_heat: 900 }, expected: 18000, tolerance: 1e-6, derivation: "0.5 x 900 x 40 = 18 000 J (aluminium)" },
    { args: { mass: 3, temperature_change: 20, specific_heat: 390 }, expected: 23400, tolerance: 1e-6, derivation: "3 x 390 x 20 = 23 400 J (copper)" },
    { args: { mass: 0.25, temperature_change: 8, specific_heat: 2100 }, expected: 4200, tolerance: 1e-6, derivation: "0.25 x 2 100 x 8 = 4 200 J (paraffin)" },
    { args: { mass: 4, temperature_change: 0, specific_heat: 4200 }, expected: 0, tolerance: 1e-9, derivation: "no change of temperature needs no heat" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "mass" },
    { kind: "increasing", arg: "temperature_change" },
    { kind: "increasing", arg: "specific_heat" },
    { kind: "homogeneous", arg: "mass", degree: 1 },
    { kind: "homogeneous", arg: "temperature_change", degree: 1 },
    { kind: "homogeneous", arg: "specific_heat", degree: 1 },
  ],
  grid: { mass: [0.25, 0.5, 2, 4], temperature_change: [1, 8, 40, 50], specific_heat: [390, 900, 2100, 4200] },
};

export function specificHeat(options: { mass: Observable<number>; temperature_change: Observable<number>; specific_heat: number }): Observable<number> {
  return model(spec, { specific_heat: options.specific_heat }, { mass: options.mass, temperature_change: options.temperature_change });
}
