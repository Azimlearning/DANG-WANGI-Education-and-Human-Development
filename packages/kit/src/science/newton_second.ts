// physics.newton_second: acceleration a = F / m (Force and Motion, Newton's second law) for a single resultant force. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.newton_second",
  exportName: "newtonSecond",
  inputs: { force: { unit: "N", min: 0 }, mass: { unit: "kg", min: 0, exclusive: true } },
  params: {},
  output: { unit: "m/s2" },
  fn: ({ force, mass }) => (force as number) / (mass as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed from F = m a.
  reference: [
    { args: { force: 10, mass: 2 }, expected: 5, tolerance: 1e-9, derivation: "10 N / 2 kg = 5 m/s2" },
    { args: { force: 6, mass: 3 }, expected: 2, tolerance: 1e-9, derivation: "6 / 3 = 2 m/s2" },
    { args: { force: 0, mass: 5 }, expected: 0, tolerance: 1e-9, derivation: "no resultant force, no acceleration" },
    { args: { force: 9.8, mass: 1 }, expected: 9.8, tolerance: 1e-9, derivation: "9.8 / 1 = 9.8 m/s2" },
    { args: { force: 15, mass: 0.5 }, expected: 30, tolerance: 1e-9, derivation: "15 / 0.5 = 30 m/s2" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "force" },
    { kind: "decreasing", arg: "mass" },
    { kind: "homogeneous", arg: "force", degree: 1 },
  ],
  grid: { force: [0.5, 2, 10, 20, 100], mass: [0.5, 1, 2, 10] },
};

export function newtonSecond(options: { force: Observable<number>; mass: Observable<number> }): Observable<number> {
  return model(spec, {}, { force: options.force, mass: options.mass });
}
