// biology.percent_change_mass: percentage change in mass = (final - initial) / initial x 100 (Movement of Substances, osmosis in plant tissue). UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.percent_change_mass",
  exportName: "percentChangeMass",
  inputs: { final_mass: { unit: "g", min: 0 } },
  params: { initial_mass: { unit: "g", min: 0, exclusive: true } },
  output: { unit: "%" },
  fn: ({ final_mass, initial_mass }) => (((final_mass as number) - (initial_mass as number)) / (initial_mass as number)) * 100,
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed: (final - initial) / initial x 100.
  reference: [
    { args: { final_mass: 12, initial_mass: 10 }, expected: 20, tolerance: 1e-9, derivation: "(12 - 10) / 10 x 100 = 20 %" },
    { args: { final_mass: 8, initial_mass: 10 }, expected: -20, tolerance: 1e-9, derivation: "(8 - 10) / 10 x 100 = -20 %" },
    { args: { final_mass: 10, initial_mass: 10 }, expected: 0, tolerance: 1e-9, derivation: "final equals initial, so no change at all" },
    { args: { final_mass: 0, initial_mass: 5 }, expected: -100, tolerance: 1e-9, derivation: "(0 - 5) / 5 x 100 = -100 %" },
    { args: { final_mass: 7.5, initial_mass: 5 }, expected: 50, tolerance: 1e-9, derivation: "(7.5 - 5) / 5 x 100 = 50 %" },
  ],
  properties: [{ kind: "finite" }, { kind: "increasing", arg: "final_mass" }, { kind: "decreasing", arg: "initial_mass" }],
  grid: { final_mass: [1, 4, 5, 8, 12], initial_mass: [2, 5, 10] },
};

export function percentChangeMass(options: { final_mass: Observable<number>; initial_mass: number }): Observable<number> {
  return model(spec, { initial_mass: options.initial_mass }, { final_mass: options.final_mass });
}
