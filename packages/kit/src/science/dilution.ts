// chemistry.dilution: concentration after dilution, M2 = M1 V1 / V2 (Acids, Bases and Salts, preparing solutions).
// Volumes are in the same unit; the final volume is at least the starting volume in a real dilution. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.dilution",
  exportName: "dilution",
  inputs: { v2: { unit: "cm3", min: 0, exclusive: true } },
  params: { m1: { unit: "mol/dm3", min: 0, exclusive: true }, v1: { unit: "cm3", min: 0, exclusive: true } },
  output: { unit: "mol/dm3" },
  fn: ({ v2, m1, v1 }) => ((m1 as number) * (v1 as number)) / (v2 as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { v2: 100, m1: 2, v1: 25 }, expected: 0.5, tolerance: 1e-12, derivation: "2.0 x 25 / 100 = 0.5 mol/dm3" },
    { args: { v2: 40, m1: 1, v1: 10 }, expected: 0.25, tolerance: 1e-12, derivation: "1.0 x 10 / 40 = 0.25" },
    { args: { v2: 50, m1: 0.5, v1: 50 }, expected: 0.5, tolerance: 1e-12, derivation: "no water added: unchanged" },
    { args: { v2: 100, m1: 4, v1: 5 }, expected: 0.2, tolerance: 1e-12, derivation: "4 x 5 / 100 = 0.2" },
    { args: { v2: 250, m1: 0.1, v1: 100 }, expected: 0.04, tolerance: 1e-12, derivation: "0.1 x 100 / 250 = 0.04" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "decreasing", arg: "v2" },
    { kind: "increasing", arg: "v1" },
    { kind: "increasing", arg: "m1" },
    { kind: "homogeneous", arg: "m1", degree: 1 },
  ],
  grid: { v2: [10, 25, 50, 100], m1: [0.1, 0.5, 1, 2], v1: [5, 10, 25, 50] },
};

export function dilution(options: { v2: Observable<number>; m1: number; v1: number }): Observable<number> {
  return model(spec, { m1: options.m1, v1: options.v1 }, { v2: options.v2 });
}
