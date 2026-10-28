// physics.parallel_resistance: the effective resistance of two resistors in parallel, 1 / R = 1 / R1 + 1 / R2 (Electricity: series and parallel circuits). Both resistances are
// inputs, in ohms; the effective resistance comes out in ohms and is always less than the smaller of the two.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.parallel_resistance",
  exportName: "parallelResistance",
  inputs: { resistance_1: { unit: "ohm", min: 0, exclusive: true }, resistance_2: { unit: "ohm", min: 0, exclusive: true } },
  params: {  },
  output: { unit: "ohm" },
  fn: ({ resistance_1, resistance_2 }) => ((resistance_1 as number) * (resistance_2 as number)) / ((resistance_1 as number) + (resistance_2 as number)),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from 1 / R = 1 / R1 + 1 / R2. The first case is the textbook's worked example (4 ohm and 12 ohm in parallel give 3 ohm).
  reference: [
    { args: { resistance_1: 4, resistance_2: 12 }, expected: 3, tolerance: 1e-9, derivation: "1/R = 1/4 + 1/12 = 4/12, so R = 3 ohm (textbook example)" },
    { args: { resistance_1: 6, resistance_2: 6 }, expected: 3, tolerance: 1e-9, derivation: "two equal resistors give half of one" },
    { args: { resistance_1: 2, resistance_2: 2 }, expected: 1, tolerance: 1e-9, derivation: "1/R = 1/2 + 1/2 = 1, so R = 1 ohm" },
    { args: { resistance_1: 10, resistance_2: 40 }, expected: 8, tolerance: 1e-9, derivation: "1/R = 1/10 + 1/40 = 5/40, so R = 8 ohm" },
    { args: { resistance_1: 3, resistance_2: 6 }, expected: 2, tolerance: 1e-9, derivation: "1/R = 1/3 + 1/6 = 1/2, so R = 2 ohm" },
    { args: { resistance_1: 5, resistance_2: 7 }, expected: 2.9166666666666665, tolerance: 1e-9, derivation: "35 / 12 ohm" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "resistance_1" },
    { kind: "increasing", arg: "resistance_2" },
  ],
  grid: { resistance_1: [2, 3, 4, 6, 10, 40], resistance_2: [2, 6, 12, 40] },
};

export function parallelResistance(options: { resistance_1: Observable<number>; resistance_2: Observable<number> }): Observable<number> {
  return model(spec, {}, { resistance_1: options.resistance_1, resistance_2: options.resistance_2 });
}
