// biology.sa_to_v_cube: surface area to volume ratio of a cube-shaped cell, 6 / side (Movement of Substances Across the Plasma Membrane).
// A cube of side s has area 6 s^2 and volume s^3, so the ratio is 6 / s. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.sa_to_v_cube",
  exportName: "surfaceAreaToVolume",
  inputs: { side: { unit: "cm", min: 0, exclusive: true } },
  params: {},
  output: { unit: "/cm" },
  fn: ({ side }) => 6 / (side as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { side: 1 }, expected: 6, tolerance: 1e-12, derivation: "area 6 cm2 over volume 1 cm3 = 6 per cm" },
    { args: { side: 2 }, expected: 3, tolerance: 1e-12, derivation: "area 24 over volume 8 = 3 per cm" },
    { args: { side: 3 }, expected: 2, tolerance: 1e-12, derivation: "area 54 over volume 27 = 2 per cm" },
    { args: { side: 0.5 }, expected: 12, tolerance: 1e-12, derivation: "area 1.5 over volume 0.125 = 12 per cm" },
    { args: { side: 6 }, expected: 1, tolerance: 1e-12, derivation: "area 216 over volume 216 = 1 per cm" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "decreasing", arg: "side" },
    { kind: "homogeneous", arg: "side", degree: -1 },
  ],
  grid: { side: [0.5, 1, 2, 3, 6] },
};

export function surfaceAreaToVolume(options: { side: Observable<number> }): Observable<number> {
  return model(spec, {  }, { side: options.side });
}
