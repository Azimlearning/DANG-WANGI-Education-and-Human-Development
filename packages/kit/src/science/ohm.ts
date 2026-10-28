// electricity.ohm: current = voltage / resistance (V = I R rearranged), steady state in an ohmic conductor.
// UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "electricity.ohm",
  exportName: "ohm",
  inputs: { voltage: { unit: "V", min: 0 }, resistance: { unit: "ohm", min: 0, exclusive: true } },
  params: {},
  output: { unit: "A" },
  fn: ({ voltage, resistance }) => (voltage as number) / (resistance as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed from I = V / R.
  reference: [
    { args: { voltage: 12, resistance: 4 }, expected: 3, tolerance: 1e-12, derivation: "12 V over 4 ohm = 3 A" },
    { args: { voltage: 6, resistance: 12 }, expected: 0.5, tolerance: 1e-12, derivation: "6 V over 12 ohm = 0.5 A" },
    { args: { voltage: 0, resistance: 10 }, expected: 0, tolerance: 1e-12, derivation: "no voltage, no current" },
    { args: { voltage: 230, resistance: 46 }, expected: 5, tolerance: 1e-12, derivation: "230 V over 46 ohm = 5 A (46 x 5 = 230)" },
    { args: { voltage: 1.5, resistance: 0.5 }, expected: 3, tolerance: 1e-12, derivation: "1.5 V over 0.5 ohm = 3 A" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "voltage" },
    { kind: "decreasing", arg: "resistance" },
    { kind: "homogeneous", arg: "voltage", degree: 1 },
  ],
  grid: { voltage: [0.5, 1.5, 6, 12, 230], resistance: [0.5, 2, 12, 46] },
};

export function ohm(options: { voltage: Observable<number>; resistance: Observable<number> }): Observable<number> {
  return model(spec, {}, { voltage: options.voltage, resistance: options.resistance });
}
