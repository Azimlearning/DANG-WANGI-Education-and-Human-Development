// chemistry.gas_volume: volume of a gas V = n x molar volume (Chemical Formulae and Equations). Molar volume is a parameter: 24 dm3/mol at room conditions, 22.4 dm3/mol at STP. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.gas_volume",
  exportName: "gasVolume",
  inputs: { moles: { unit: "mol", min: 0 } },
  params: { molar_volume: { unit: "dm3/mol", min: 0, exclusive: true } },
  output: { unit: "dm3" },
  fn: ({ moles, molar_volume }) => (moles as number) * (molar_volume as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed: n x molar volume.
  reference: [
    { args: { moles: 2, molar_volume: 24 }, expected: 48, tolerance: 1e-9, derivation: "2 mol x 24 dm3/mol = 48 dm3" },
    { args: { moles: 0.5, molar_volume: 22.4 }, expected: 11.2, tolerance: 1e-9, derivation: "0.5 x 22.4 = 11.2 dm3" },
    { args: { moles: 1, molar_volume: 24 }, expected: 24, tolerance: 1e-9, derivation: "1 x 24 = 24 dm3" },
    { args: { moles: 0, molar_volume: 24 }, expected: 0, tolerance: 1e-9, derivation: "no gas, no volume" },
    { args: { moles: 0.25, molar_volume: 24 }, expected: 6, tolerance: 1e-9, derivation: "0.25 x 24 = 6 dm3" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "moles" },
    { kind: "increasing", arg: "molar_volume" },
    { kind: "homogeneous", arg: "moles", degree: 1 },
  ],
  grid: { moles: [0.1, 0.5, 1, 2, 5], molar_volume: [22.4, 24] },
};

export function gasVolume(options: { moles: Observable<number>; molar_volume: number }): Observable<number> {
  return model(spec, { molar_volume: options.molar_volume }, { moles: options.moles });
}
