// biology.respiration_energy: the energy released when an amount of glucose is broken down, E = n x e, where e is the energy one mole of glucose gives by the pathway: 210 kJ by alcohol
// fermentation, 150 kJ by lactic acid fermentation, 2898 kJ by aerobic respiration (Cellular Respiration, Table 7.1). The textbook words these per "molecule"; kilojoules for a
// single molecule would be absurd, so they are read as per mole (ASSUMED, D-46). UNVERIFIED until the corpus is loaded (P2); the citation pointers name the textbook pages.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.respiration_energy",
  exportName: "respirationEnergy",
  inputs: { glucose: { unit: "mol", min: 0 } },
  params: { energy_per_mole: { unit: "kJ/mol", min: 0, exclusive: true } },
  output: { unit: "kJ" },
  fn: ({ glucose, energy_per_mole }) => (glucose as number) * (energy_per_mole as number),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { glucose: 1, energy_per_mole: 210 }, expected: 210, tolerance: 1e-9, derivation: "1 mol x 210 kJ/mol = 210 kJ (alcohol fermentation)" },
    { args: { glucose: 1, energy_per_mole: 2898 }, expected: 2898, tolerance: 1e-9, derivation: "1 mol x 2898 kJ/mol = 2898 kJ (aerobic respiration)" },
    { args: { glucose: 0.5, energy_per_mole: 150 }, expected: 75, tolerance: 1e-9, derivation: "0.5 mol x 150 kJ/mol = 75 kJ (lactic acid fermentation)" },
    { args: { glucose: 0.004, energy_per_mole: 210 }, expected: 0.84, tolerance: 1e-9, derivation: "0.004 x 210 = 0.84 kJ" },
    { args: { glucose: 0, energy_per_mole: 210 }, expected: 0, tolerance: 1e-9, derivation: "no glucose broken down releases no energy" },
  ],
  properties: [{ kind: "finite" }, { kind: "non_negative" }, { kind: "increasing", arg: "glucose" }, { kind: "increasing", arg: "energy_per_mole" }, { kind: "homogeneous", arg: "glucose", degree: 1 }],
  grid: { glucose: [0.001, 0.0025, 0.004, 0.5, 1], energy_per_mole: [150, 210, 2898] },
};

export function respirationEnergy(options: { glucose: Observable<number>; energy_per_mole: number }): Observable<number> {
  return model(spec, { energy_per_mole: options.energy_per_mole }, { glucose: options.glucose });
}
