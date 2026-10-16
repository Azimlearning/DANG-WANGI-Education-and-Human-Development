// fluids.pressure_depth: gauge pressure at a depth in a liquid, P = h rho g. UNVERIFIED until the corpus exists (P2).
// The value of g is a parameter, recorded in the provenance, because textbooks differ (9.81 or 10 m/s2) and the student should see which.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "fluids.pressure_depth",
  exportName: "pressureDepth",
  inputs: { depth: { unit: "m", min: 0 } },
  params: { density: { unit: "kg/m3", min: 0, exclusive: true }, g: { unit: "m/s2", min: 0, exclusive: true } },
  output: { unit: "Pa" },
  fn: ({ depth, density, g }) => (depth as number) * (density as number) * (g as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed from P = h rho g.
  reference: [
    { args: { depth: 2, density: 1000, g: 10 }, expected: 20000, tolerance: 1e-9, derivation: "2 m x 1000 kg/m3 x 10 m/s2 = 20 000 Pa" },
    { args: { depth: 10, density: 1000, g: 9.81 }, expected: 98100, tolerance: 1e-9, derivation: "10 x 1000 x 9.81 = 98 100 Pa" },
    { args: { depth: 0, density: 1000, g: 10 }, expected: 0, tolerance: 1e-12, derivation: "at the surface the gauge pressure is zero" },
    { args: { depth: 0.5, density: 13600, g: 10 }, expected: 68000, tolerance: 1e-9, derivation: "0.5 x 13 600 x 10 = 68 000 Pa (mercury)" },
    { args: { depth: 3, density: 1030, g: 10 }, expected: 30900, tolerance: 1e-9, derivation: "3 x 1030 x 10 = 30 900 Pa (sea water)" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "depth" },
    { kind: "increasing", arg: "density" },
    { kind: "increasing", arg: "g" },
    { kind: "homogeneous", arg: "depth", degree: 1 },
  ],
  grid: { depth: [0.5, 1, 2, 5, 10], density: [800, 1000, 1030, 13600], g: [9.78, 9.81, 10] },
};

export function pressureDepth(options: { depth: Observable<number>; density: number; g: number }): Observable<number> {
  return model(spec, { density: options.density, g: options.g }, { depth: options.depth });
}
