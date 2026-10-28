// physics.transformer_voltage: the output voltage of an ideal transformer from its turns, Vs / Vp = Ns / Np (Electromagnetism: transformers). The numbers of turns are
// counts (above zero); the input voltage is in volts; the output voltage comes out in volts. "Ideal" means no energy is lost, as the textbook assumes.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.transformer_voltage",
  exportName: "transformerVoltage",
  inputs: { primary_turns: { unit: "turns", min: 0, exclusive: true }, secondary_turns: { unit: "turns", min: 0, exclusive: true } },
  params: { primary_voltage: { unit: "V", min: 0, exclusive: true } },
  output: { unit: "V" },
  fn: ({ primary_turns, secondary_turns, primary_voltage }) => ((primary_voltage as number) * (secondary_turns as number)) / (primary_turns as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from Vs = Vp x Ns / Np. The first case is the worked example in the textbook (240 V to 18 V with 800 and 60 turns).
  reference: [
    { args: { primary_turns: 800, secondary_turns: 60, primary_voltage: 240 }, expected: 18, tolerance: 1e-9, derivation: "240 x 60 / 800 = 18 V (step-down)" },
    { args: { primary_turns: 100, secondary_turns: 500, primary_voltage: 12 }, expected: 60, tolerance: 1e-9, derivation: "12 x 500 / 100 = 60 V (step-up)" },
    { args: { primary_turns: 400, secondary_turns: 400, primary_voltage: 9 }, expected: 9, tolerance: 1e-9, derivation: "equal turns leave the voltage unchanged" },
    { args: { primary_turns: 50, secondary_turns: 1000, primary_voltage: 6 }, expected: 120, tolerance: 1e-9, derivation: "6 x 1 000 / 50 = 120 V" },
    { args: { primary_turns: 1200, secondary_turns: 30, primary_voltage: 240 }, expected: 6, tolerance: 1e-9, derivation: "240 x 30 / 1 200 = 6 V" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "secondary_turns" },
    { kind: "decreasing", arg: "primary_turns" },
    { kind: "increasing", arg: "primary_voltage" },
    { kind: "homogeneous", arg: "secondary_turns", degree: 1 },
    { kind: "homogeneous", arg: "primary_turns", degree: -1 },
    { kind: "homogeneous", arg: "primary_voltage", degree: 1 },
  ],
  grid: { primary_turns: [50, 100, 400, 800], secondary_turns: [30, 60, 500, 1000], primary_voltage: [6, 12, 240] },
};

export function transformerVoltage(options: { primary_turns: Observable<number>; secondary_turns: Observable<number>; primary_voltage: number }): Observable<number> {
  return model(spec, { primary_voltage: options.primary_voltage }, { primary_turns: options.primary_turns, secondary_turns: options.secondary_turns });
}
