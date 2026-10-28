// chemistry.titration_concentration: concentration of the base from a titration, Mb = Ma Va b / (a Vb) for a A + b B (Acids, Bases and Salts).
// Volumes are in the same unit; coefficients a and b come from the balanced equation. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.titration_concentration",
  exportName: "titration",
  inputs: { va: { unit: "cm3", min: 0, exclusive: true }, vb: { unit: "cm3", min: 0, exclusive: true } },
  params: { ma: { unit: "mol/dm3", min: 0, exclusive: true }, acid_coeff: { unit: "1", min: 0, exclusive: true }, base_coeff: { unit: "1", min: 0, exclusive: true } },
  output: { unit: "mol/dm3" },
  fn: ({ va, vb, ma, acid_coeff, base_coeff }) => ((ma as number) * (va as number) * (base_coeff as number)) / ((acid_coeff as number) * (vb as number)),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { va: 25, vb: 20, ma: 0.1, acid_coeff: 1, base_coeff: 1 }, expected: 0.125, tolerance: 1e-12, derivation: "0.1 x 25 x 1 / (1 x 20) = 0.125 mol/dm3" },
    { args: { va: 25, vb: 20, ma: 0.1, acid_coeff: 1, base_coeff: 2 }, expected: 0.25, tolerance: 1e-12, derivation: "0.1 x 25 x 2 / (1 x 20) = 0.25 (H2SO4 + 2NaOH)" },
    { args: { va: 10, vb: 40, ma: 0.2, acid_coeff: 2, base_coeff: 1 }, expected: 0.025, tolerance: 1e-12, derivation: "0.2 x 10 x 1 / (2 x 40) = 0.025" },
    { args: { va: 20, vb: 20, ma: 1, acid_coeff: 1, base_coeff: 1 }, expected: 1, tolerance: 1e-12, derivation: "equal volumes, equal strengths: 1" },
    { args: { va: 50, vb: 25, ma: 0.1, acid_coeff: 1, base_coeff: 1 }, expected: 0.2, tolerance: 1e-12, derivation: "0.1 x 50 / 25 = 0.2" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "va" },
    { kind: "decreasing", arg: "vb" },
    { kind: "increasing", arg: "ma" },
    { kind: "increasing", arg: "base_coeff" },
    { kind: "decreasing", arg: "acid_coeff" },
    { kind: "homogeneous", arg: "ma", degree: 1 },
  ],
  grid: { va: [5, 10, 25, 50], vb: [5, 10, 20, 40], ma: [0.05, 0.1, 0.5, 1], acid_coeff: [1, 2, 3], base_coeff: [1, 2, 3] },
};

export function titration(options: { va: Observable<number>; vb: Observable<number>; ma: number; acid_coeff: number; base_coeff: number }): Observable<number> {
  return model(spec, { ma: options.ma, acid_coeff: options.acid_coeff, base_coeff: options.base_coeff }, { va: options.va, vb: options.vb });
}
