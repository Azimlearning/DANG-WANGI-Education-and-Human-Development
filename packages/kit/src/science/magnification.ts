// biology.magnification: magnification = image size / actual size (microscopy, Cell Structure and Function).
// Both sizes are in the same unit. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.magnification",
  exportName: "magnification",
  inputs: { image: { unit: "mm", min: 0 }, actual: { unit: "mm", min: 0, exclusive: true } },
  params: {},
  output: { unit: "times" },
  fn: ({ image, actual }) => (image as number) / (actual as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { image: 50, actual: 0.5 }, expected: 100, tolerance: 1e-9, derivation: "50 mm / 0.5 mm = 100 times" },
    { args: { image: 30, actual: 0.02 }, expected: 1500, tolerance: 1e-9, derivation: "30 / 0.02 = 1500 times" },
    { args: { image: 0, actual: 0.1 }, expected: 0, tolerance: 1e-12, derivation: "no image, no magnification" },
    { args: { image: 12, actual: 0.04 }, expected: 300, tolerance: 1e-9, derivation: "12 / 0.04 = 300 times" },
    { args: { image: 100, actual: 2 }, expected: 50, tolerance: 1e-9, derivation: "100 / 2 = 50 times" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "image" },
    { kind: "decreasing", arg: "actual" },
    { kind: "homogeneous", arg: "image", degree: 1 },
  ],
  grid: { image: [1, 5, 10, 50, 100], actual: [0.01, 0.05, 0.2, 1] },
};

export function magnification(options: { image: Observable<number>; actual: Observable<number> }): Observable<number> {
  return model(spec, {  }, { image: options.image, actual: options.actual });
}
