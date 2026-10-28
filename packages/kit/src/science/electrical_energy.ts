// physics.electrical_energy: the electrical energy a device uses, E = V I t (Electricity: electrical energy and power). Current in amperes, time in seconds, the potential
// difference in volts as a parameter; the energy comes out in joules.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.electrical_energy",
  exportName: "electricalEnergy",
  inputs: { current: { unit: "A", min: 0 }, time: { unit: "s", min: 0 } },
  params: { voltage: { unit: "V", min: 0, exclusive: true } },
  output: { unit: "J" },
  fn: ({ current, time, voltage }) => (voltage as number) * (current as number) * (time as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from E = V I t. The first case is the textbook's lamp example (6 V, 0.7 A, one minute gives 252 J).
  reference: [
    { args: { current: 0.7, time: 60, voltage: 6 }, expected: 252, tolerance: 1e-9, derivation: "6 x 0.7 x 60 = 252 J (textbook lamp)" },
    { args: { current: 1.5, time: 120, voltage: 12 }, expected: 2160, tolerance: 1e-9, derivation: "12 x 1.5 x 120 = 2 160 J" },
    { args: { current: 0, time: 60, voltage: 6 }, expected: 0, tolerance: 1e-12, derivation: "no current means no energy" },
    { args: { current: 0.2, time: 3600, voltage: 240 }, expected: 172800, tolerance: 1e-9, derivation: "240 x 0.2 x 3 600 = 172 800 J" },
    { args: { current: 0.35, time: 45, voltage: 6 }, expected: 94.5, tolerance: 1e-9, derivation: "6 x 0.35 x 45 = 94.5 J" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "current" },
    { kind: "increasing", arg: "time" },
    { kind: "increasing", arg: "voltage" },
    { kind: "homogeneous", arg: "current", degree: 1 },
    { kind: "homogeneous", arg: "time", degree: 1 },
    { kind: "homogeneous", arg: "voltage", degree: 1 },
  ],
  grid: { current: [0.1, 0.7, 1.5, 2], time: [10, 60, 120, 3600], voltage: [3, 6, 12, 240] },
};

export function electricalEnergy(options: { current: Observable<number>; time: Observable<number>; voltage: number }): Observable<number> {
  return model(spec, { voltage: options.voltage }, { current: options.current, time: options.time });
}
