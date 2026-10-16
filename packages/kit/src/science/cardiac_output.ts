// biology.cardiac_output: cardiac output = heart rate x stroke volume (Circulatory System). Beats per minute and millilitres per beat give litres per minute. UNVERIFIED until the corpus exists (P2).
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "biology.cardiac_output",
  exportName: "cardiacOutput",
  inputs: { heart_rate: { unit: "beats/min", min: 0 }, stroke_volume: { unit: "mL", min: 0 } },
  params: {},
  output: { unit: "L/min" },
  fn: ({ heart_rate, stroke_volume }) => ((heart_rate as number) * (stroke_volume as number)) / 1000,
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Hand-computed: beats/min x mL/beat gives mL/min; divide by 1000 for L/min.
  reference: [
    { args: { heart_rate: 72, stroke_volume: 70 }, expected: 5.04, tolerance: 1e-9, derivation: "72 x 70 = 5040 mL/min = 5.04 L/min" },
    { args: { heart_rate: 60, stroke_volume: 80 }, expected: 4.8, tolerance: 1e-9, derivation: "60 x 80 = 4800 mL/min = 4.8 L/min" },
    { args: { heart_rate: 100, stroke_volume: 100 }, expected: 10, tolerance: 1e-9, derivation: "100 x 100 = 10000 mL/min = 10 L/min" },
    { args: { heart_rate: 0, stroke_volume: 70 }, expected: 0, tolerance: 1e-9, derivation: "no beats, no output" },
    { args: { heart_rate: 150, stroke_volume: 120 }, expected: 18, tolerance: 1e-9, derivation: "150 x 120 = 18000 mL/min = 18 L/min" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "heart_rate" },
    { kind: "increasing", arg: "stroke_volume" },
    { kind: "homogeneous", arg: "heart_rate", degree: 1 },
    { kind: "homogeneous", arg: "stroke_volume", degree: 1 },
  ],
  grid: { heart_rate: [40, 60, 72, 100, 180], stroke_volume: [30, 50, 70, 100, 120] },
};

export function cardiacOutput(options: { heart_rate: Observable<number>; stroke_volume: Observable<number> }): Observable<number> {
  return model(spec, {}, { heart_rate: options.heart_rate, stroke_volume: options.stroke_volume });
}
