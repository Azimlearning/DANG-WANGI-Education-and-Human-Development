// biology.photosynthesis_net: net carbon dioxide uptake of a leaf against light intensity, Pmax I / (K + I) minus respiration (Leaf Structure and Function, compensation point).
// A STYLISED saturating curve for teaching, not measured data: it shows the compensation point (net uptake zero) and saturation. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.photosynthesis_net",
  exportName: "netPhotosynthesis",
  inputs: { light: { unit: "klux", min: 0 } },
  params: { pmax: { unit: "mg/h", min: 0, exclusive: true }, k: { unit: "klux", min: 0, exclusive: true }, resp: { unit: "mg/h", min: 0 } },
  output: { unit: "mg/h" },
  fn: ({ light, pmax, k, resp }) => ((pmax as number) * (light as number)) / ((k as number) + (light as number)) - (resp as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { light: 4, pmax: 10, k: 4, resp: 2 }, expected: 3, tolerance: 1e-9, derivation: "10 x 4 / (4 + 4) = 5, minus 2 = 3 mg/h" },
    { args: { light: 0, pmax: 10, k: 4, resp: 2 }, expected: -2, tolerance: 1e-9, derivation: "no light: 0 minus respiration 2 = -2 mg/h" },
    { args: { light: 1, pmax: 10, k: 4, resp: 2 }, expected: 0, tolerance: 1e-9, derivation: "10 x 1 / 5 = 2, minus 2 = 0: the compensation point" },
    { args: { light: 16, pmax: 10, k: 4, resp: 2 }, expected: 6, tolerance: 1e-9, derivation: "10 x 16 / 20 = 8, minus 2 = 6 mg/h" },
    { args: { light: 12, pmax: 10, k: 4, resp: 2 }, expected: 5.5, tolerance: 1e-9, derivation: "10 x 12 / 16 = 7.5, minus 2 = 5.5 mg/h" },
    { args: { light: 2, pmax: 6, k: 2, resp: 1 }, expected: 2, tolerance: 1e-9, derivation: "6 x 2 / 4 = 3, minus 1 = 2 mg/h" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "increasing", arg: "light" },
    { kind: "increasing", arg: "pmax" },
    { kind: "decreasing", arg: "k" },
    { kind: "decreasing", arg: "resp" },
  ],
  grid: { light: [0.5, 1, 2, 4, 8, 16], pmax: [4, 6, 10, 20], k: [1, 2, 4, 8], resp: [0, 1, 2, 3] },
};

export function netPhotosynthesis(options: { light: Observable<number>; pmax: number; k: number; resp: number }): Observable<number> {
  return model(spec, { pmax: options.pmax, k: options.k, resp: options.resp }, { light: options.light });
}
