// chemistry.titration_endpoint_volume: the volume of base needed to reach the end point of a titration, Vb = Ma Va b / (a Mb) for a A + b B (Acids, Bases and Salts).
// The same relation as `chemistry.titration_concentration` read the other way round: given the base's concentration, how much of it neutralises the acid. A bench uses it to
// decide where the indicator changes colour. UNVERIFIED until the corpus is loaded (P2); the citation pointers name the textbook pages.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.titration_endpoint_volume",
  exportName: "titrationEndpoint",
  inputs: { va: { unit: "cm3", min: 0, exclusive: true }, mb: { unit: "mol/dm3", min: 0, exclusive: true } },
  params: { ma: { unit: "mol/dm3", min: 0, exclusive: true }, acid_coeff: { unit: "1", min: 0, exclusive: true }, base_coeff: { unit: "1", min: 0, exclusive: true } },
  output: { unit: "cm3" },
  fn: ({ va, mb, ma, acid_coeff, base_coeff }) => ((ma as number) * (va as number) * (base_coeff as number)) / ((acid_coeff as number) * (mb as number)),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { va: 25, mb: 0.125, ma: 0.1, acid_coeff: 1, base_coeff: 1 }, expected: 20, tolerance: 1e-12, derivation: "0.1 x 25 x 1 / (1 x 0.125) = 2.5 / 0.125 = 20 cm3" },
    { args: { va: 25, mb: 0.25, ma: 0.1, acid_coeff: 1, base_coeff: 2 }, expected: 20, tolerance: 1e-12, derivation: "0.1 x 25 x 2 / (1 x 0.25) = 5 / 0.25 = 20 cm3 (H2SO4 + 2NaOH)" },
    { args: { va: 10, mb: 0.025, ma: 0.2, acid_coeff: 2, base_coeff: 1 }, expected: 40, tolerance: 1e-12, derivation: "0.2 x 10 x 1 / (2 x 0.025) = 2 / 0.05 = 40 cm3" },
    { args: { va: 20, mb: 1, ma: 1, acid_coeff: 1, base_coeff: 1 }, expected: 20, tolerance: 1e-12, derivation: "equal strengths: the same volume, 20 cm3" },
    { args: { va: 50, mb: 0.2, ma: 0.1, acid_coeff: 1, base_coeff: 1 }, expected: 25, tolerance: 1e-12, derivation: "0.1 x 50 / 0.2 = 5 / 0.2 = 25 cm3" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "va" },
    { kind: "decreasing", arg: "mb" },
    { kind: "increasing", arg: "ma" },
    { kind: "increasing", arg: "base_coeff" },
    { kind: "decreasing", arg: "acid_coeff" },
    { kind: "homogeneous", arg: "ma", degree: 1 },
  ],
  grid: { va: [5, 10, 25, 50], mb: [0.05, 0.1, 0.5, 1], ma: [0.05, 0.1, 0.5, 1], acid_coeff: [1, 2, 3], base_coeff: [1, 2, 3] },
};

export function titrationEndpoint(options: { va: Observable<number>; mb: Observable<number>; ma: number; acid_coeff: number; base_coeff: number }): Observable<number> {
  return model(spec, { ma: options.ma, acid_coeff: options.acid_coeff, base_coeff: options.base_coeff }, { va: options.va, mb: options.mb });
}
