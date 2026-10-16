// chemistry.moles_from_mass: amount of substance n = mass / molar mass (Chemical Formulae and Equations, the mole).
// Mass in grams, molar mass in grams per mole. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.moles_from_mass",
  exportName: "moles",
  inputs: { mass: { unit: "g", min: 0 } },
  params: { molar_mass: { unit: "g/mol", min: 0, exclusive: true } },
  output: { unit: "mol" },
  fn: ({ mass, molar_mass }) => (mass as number) / (molar_mass as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { mass: 36, molar_mass: 18 }, expected: 2, tolerance: 1e-12, derivation: "36 g / 18 g per mol = 2 mol" },
    { args: { mass: 44, molar_mass: 44 }, expected: 1, tolerance: 1e-12, derivation: "44 / 44 = 1 mol" },
    { args: { mass: 0, molar_mass: 18 }, expected: 0, tolerance: 1e-12, derivation: "no mass, no moles" },
    { args: { mass: 5.85, molar_mass: 58.5 }, expected: 0.1, tolerance: 1e-12, derivation: "5.85 / 58.5 = 0.1 mol" },
    { args: { mass: 12, molar_mass: 24 }, expected: 0.5, tolerance: 1e-12, derivation: "12 / 24 = 0.5 mol" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "mass" },
    { kind: "decreasing", arg: "molar_mass" },
    { kind: "homogeneous", arg: "mass", degree: 1 },
  ],
  grid: { mass: [1, 5, 12, 36, 100], molar_mass: [2, 18, 44, 58.5] },
};

export function moles(options: { mass: Observable<number>; molar_mass: number }): Observable<number> {
  return model(spec, { molar_mass: options.molar_mass }, { mass: options.mass });
}
