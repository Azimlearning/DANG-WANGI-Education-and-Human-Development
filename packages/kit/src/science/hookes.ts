// mechanics.hookes: extension = load / k, within the elastic limit. P0's model, moved into the registration framework.
// The citation stays UNVERIFIED until the corpus exists (P2, hard constraint 4).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "mechanics.hookes",
  exportName: "hookes",
  inputs: { load: { unit: "N", min: 0 } },
  params: { k: { unit: "N/m", min: 0, exclusive: true } },
  output: { unit: "m" },
  fn: ({ load, k }) => (load as number) / (k as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed from F = k x rearranged as x = F / k; one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { k: 50, load: 10 }, expected: 0.2, tolerance: 1e-12, derivation: "10 N over 50 N/m = 0.2 m" },
    { args: { k: 50, load: 2 }, expected: 0.04, tolerance: 1e-12, derivation: "2 N over 50 N/m = 0.04 m" },
    { args: { k: 20, load: 4 }, expected: 0.2, tolerance: 1e-12, derivation: "4 N over 20 N/m = 0.2 m" },
    { args: { k: 100, load: 0 }, expected: 0, tolerance: 1e-12, derivation: "no load, no extension" },
    { args: { k: 250, load: 5 }, expected: 0.02, tolerance: 1e-12, derivation: "5 N over 250 N/m = 0.02 m" },
    { args: { k: 0.5, load: 1 }, expected: 2, tolerance: 1e-12, derivation: "1 N over 0.5 N/m = 2 m (a very soft spring)" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "load" },
    { kind: "decreasing", arg: "k" },
    { kind: "homogeneous", arg: "load", degree: 1 },
  ],
  grid: { load: [0.5, 1, 2, 5, 10], k: [1, 10, 50, 200] },
};

export function hookes(options: { k: number; load: Observable<number> }): Observable<number> {
  return model(spec, { k: options.k }, { load: options.load });
}
