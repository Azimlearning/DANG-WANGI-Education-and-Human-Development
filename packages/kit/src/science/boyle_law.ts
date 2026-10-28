// physics.boyle_law: the pressure of a fixed mass of gas at constant temperature after its volume changes, P1 V1 = P2 V2 (Heat: Boyle's law). The starting pressure and volume
// are parameters; the final volume is the input and the final pressure comes out. Pressure in kPa and volume in cm3 (any one unit for both volumes gives the same ratio).
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.boyle_law",
  exportName: "boyleLaw",
  inputs: { final_volume: { unit: "cm3", min: 0, exclusive: true } },
  params: { initial_pressure: { unit: "kPa", min: 0, exclusive: true }, initial_volume: { unit: "cm3", min: 0, exclusive: true } },
  output: { unit: "kPa" },
  fn: ({ final_volume, initial_pressure, initial_volume }) => ((initial_pressure as number) * (initial_volume as number)) / (final_volume as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from P1 V1 = P2 V2. The first case is the textbook's syringe example (108 kPa, 60 cm3 compressed to 48 cm3).
  reference: [
    { args: { final_volume: 48, initial_pressure: 108, initial_volume: 60 }, expected: 135, tolerance: 1e-9, derivation: "108 x 60 / 48 = 135 kPa (syringe)" },
    { args: { final_volume: 25, initial_pressure: 100, initial_volume: 50 }, expected: 200, tolerance: 1e-9, derivation: "100 x 50 / 25 = 200 kPa" },
    { args: { final_volume: 100, initial_pressure: 100, initial_volume: 50 }, expected: 50, tolerance: 1e-9, derivation: "100 x 50 / 100 = 50 kPa" },
    { args: { final_volume: 40, initial_pressure: 101, initial_volume: 40 }, expected: 101, tolerance: 1e-9, derivation: "unchanged volume leaves the pressure unchanged" },
    { args: { final_volume: 48, initial_pressure: 101, initial_volume: 60 }, expected: 126.25, tolerance: 1e-9, derivation: "101 x 60 / 48 = 126.25 kPa" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "decreasing", arg: "final_volume" },
    { kind: "increasing", arg: "initial_pressure" },
    { kind: "increasing", arg: "initial_volume" },
    { kind: "homogeneous", arg: "final_volume", degree: -1 },
    { kind: "homogeneous", arg: "initial_pressure", degree: 1 },
    { kind: "homogeneous", arg: "initial_volume", degree: 1 },
  ],
  grid: { final_volume: [20, 30, 48, 60, 120], initial_pressure: [100, 101, 108], initial_volume: [40, 60, 100] },
};

export function boyleLaw(options: { final_volume: Observable<number>; initial_pressure: number; initial_volume: number }): Observable<number> {
  return model(spec, { initial_pressure: options.initial_pressure, initial_volume: options.initial_volume }, { final_volume: options.final_volume });
}
