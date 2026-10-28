// chemistry.average_rate: average rate of reaction = quantity of product / time (Rate of Reaction).
// Volume of gas in cm3, time in seconds. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "chemistry.average_rate",
  exportName: "averageRate",
  inputs: { volume: { unit: "cm3", min: 0 }, time: { unit: "s", min: 0, exclusive: true } },
  params: {},
  output: { unit: "cm3/s" },
  fn: ({ volume, time }) => (volume as number) / (time as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Hand-computed, one line of arithmetic each. Not run through the implementation.
  reference: [
    { args: { volume: 24, time: 60 }, expected: 0.4, tolerance: 1e-12, derivation: "24 cm3 / 60 s = 0.4 cm3 per s" },
    { args: { volume: 50, time: 100 }, expected: 0.5, tolerance: 1e-12, derivation: "50 / 100 = 0.5" },
    { args: { volume: 0, time: 30 }, expected: 0, tolerance: 1e-12, derivation: "no gas, no rate" },
    { args: { volume: 36, time: 12 }, expected: 3, tolerance: 1e-12, derivation: "36 / 12 = 3" },
    { args: { volume: 5, time: 2 }, expected: 2.5, tolerance: 1e-12, derivation: "5 / 2 = 2.5" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "volume" },
    { kind: "decreasing", arg: "time" },
    { kind: "homogeneous", arg: "volume", degree: 1 },
  ],
  grid: { volume: [5, 24, 50], time: [2, 12, 60, 100] },
};

export function averageRate(options: { volume: Observable<number>; time: Observable<number> }): Observable<number> {
  return model(spec, {  }, { volume: options.volume, time: options.time });
}
