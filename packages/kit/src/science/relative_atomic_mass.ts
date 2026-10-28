// chemistry.relative_atomic_mass: the relative atomic mass of an element with two isotopes, the sum of (% of the isotope x its mass) divided by 100 (Matter and the Atomic Structure:
// isotopes). The abundance of the first isotope is a percentage from 0 to 100; the second makes up the rest. Masses are relative isotopic masses (nucleon numbers).
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.relative_atomic_mass",
  exportName: "relativeAtomicMass",
  inputs: { abundance_1: { unit: "%", min: 0, max: 100 } },
  params: { mass_1: { unit: "u", min: 0, exclusive: true }, mass_2: { unit: "u", min: 0, exclusive: true } },
  output: { unit: "u" },
  fn: ({ abundance_1, mass_1, mass_2 }) => ((abundance_1 as number) * (mass_1 as number) + (100 - (abundance_1 as number)) * (mass_2 as number)) / 100,
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from (% x mass + % x mass) / 100. The first case is the textbook's chlorine example (75 percent chlorine-35, 25 percent chlorine-37).
  reference: [
    { args: { abundance_1: 75, mass_1: 35, mass_2: 37 }, expected: 35.5, tolerance: 1e-9, derivation: "(75 x 35 + 25 x 37) / 100 = 35.5 (chlorine)" },
    { args: { abundance_1: 20, mass_1: 10, mass_2: 11 }, expected: 10.8, tolerance: 1e-9, derivation: "(20 x 10 + 80 x 11) / 100 = 10.8" },
    { args: { abundance_1: 70, mass_1: 63, mass_2: 65 }, expected: 63.6, tolerance: 1e-9, derivation: "(70 x 63 + 30 x 65) / 100 = 63.6" },
    { args: { abundance_1: 50, mass_1: 12, mass_2: 14 }, expected: 13, tolerance: 1e-9, derivation: "equal abundances give the plain average, 13" },
    { args: { abundance_1: 100, mass_1: 35, mass_2: 37 }, expected: 35, tolerance: 1e-9, derivation: "all of the first isotope gives its mass" },
    { args: { abundance_1: 0, mass_1: 35, mass_2: 37 }, expected: 37, tolerance: 1e-9, derivation: "none of the first isotope gives the second mass" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "mass_1" },
    { kind: "increasing", arg: "mass_2" },
  ],
  grid: { abundance_1: [25, 50, 75, 80], mass_1: [10, 35, 63], mass_2: [11, 37, 65] },
};

export function relativeAtomicMass(options: { abundance_1: Observable<number>; mass_1: number; mass_2: number }): Observable<number> {
  return model(spec, { mass_1: options.mass_1, mass_2: options.mass_2 }, { abundance_1: options.abundance_1 });
}
