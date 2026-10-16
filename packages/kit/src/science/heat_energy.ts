// chemistry.heat_energy: heat energy Q = m c (change in temperature) (Thermochemistry, heat of reaction).
// Mass in grams, specific heat capacity in joules per gram per degree Celsius. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.heat_energy",
  exportName: "heatEnergy",
  inputs: { delta_t: { unit: "°C", min: 0 } },
  params: { mass: { unit: "g", min: 0, exclusive: true }, c: { unit: "J/(g°C)", min: 0, exclusive: true } },
  output: { unit: "J" },
  fn: ({ delta_t, mass, c }) => (mass as number) * (c as number) * (delta_t as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { delta_t: 5, mass: 100, c: 4.2 }, expected: 2100, tolerance: 1e-9, derivation: "100 x 4.2 x 5 = 2100 J" },
    { args: { delta_t: 6.5, mass: 50, c: 4.2 }, expected: 1365, tolerance: 1e-9, derivation: "50 x 4.2 x 6.5 = 1365 J" },
    { args: { delta_t: 0, mass: 200, c: 4.2 }, expected: 0, tolerance: 1e-12, derivation: "no temperature change, no heat" },
    { args: { delta_t: 10, mass: 25, c: 2 }, expected: 500, tolerance: 1e-9, derivation: "25 x 2 x 10 = 500 J" },
    { args: { delta_t: 3, mass: 100, c: 4 }, expected: 1200, tolerance: 1e-9, derivation: "100 x 4 x 3 = 1200 J" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "delta_t" },
    { kind: "increasing", arg: "mass" },
    { kind: "increasing", arg: "c" },
    { kind: "homogeneous", arg: "delta_t", degree: 1 },
  ],
  grid: { delta_t: [0.5, 1, 2, 5, 10], mass: [25, 50, 100, 200], c: [2, 4.2, 4.5] },
};

export function heatEnergy(options: { delta_t: Observable<number>; mass: number; c: number }): Observable<number> {
  return model(spec, { mass: options.mass, c: options.c }, { delta_t: options.delta_t });
}
