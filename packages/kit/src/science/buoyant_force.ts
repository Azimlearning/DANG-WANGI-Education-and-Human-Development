// physics.buoyant_force: the buoyant force on an object in a fluid, the weight of the fluid it displaces, F = rho V g (Pressure: Archimedes' principle). Volume in cubic metres,
// density in kg/m3, g in m/s2 (a parameter, because textbooks differ); the force comes out in newtons.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.buoyant_force",
  exportName: "buoyantForce",
  inputs: { volume: { unit: "m3", min: 0 } },
  params: { density: { unit: "kg/m3", min: 0, exclusive: true }, g: { unit: "m/s2", min: 0, exclusive: true } },
  output: { unit: "N" },
  fn: ({ volume, density, g }) => (volume as number) * (density as number) * (g as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from F = rho V g, the weight of the fluid displaced.
  reference: [
    { args: { volume: 0.002, density: 1000, g: 10 }, expected: 20, tolerance: 1e-9, derivation: "0.002 x 1000 x 10 = 20 N" },
    { args: { volume: 0.001, density: 1000, g: 9.81 }, expected: 9.81, tolerance: 1e-9, derivation: "0.001 x 1000 x 9.81 = 9.81 N" },
    { args: { volume: 0.0005, density: 1030, g: 9.81 }, expected: 5.05215, tolerance: 1e-9, derivation: "0.0005 x 1030 x 9.81 = 5.05215 N (sea water)" },
    { args: { volume: 0.004, density: 13600, g: 10 }, expected: 544, tolerance: 1e-9, derivation: "0.004 x 13 600 x 10 = 544 N (mercury)" },
    { args: { volume: 0, density: 1000, g: 10 }, expected: 0, tolerance: 1e-12, derivation: "no fluid displaced means no buoyant force" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "volume" },
    { kind: "increasing", arg: "density" },
    { kind: "increasing", arg: "g" },
    { kind: "homogeneous", arg: "volume", degree: 1 },
    { kind: "homogeneous", arg: "density", degree: 1 },
    { kind: "homogeneous", arg: "g", degree: 1 },
  ],
  grid: { volume: [0.0005, 0.001, 0.002, 0.005], density: [800, 1000, 1030, 13600], g: [9.78, 9.81, 10] },
};

export function buoyantForce(options: { volume: Observable<number>; density: number; g: number }): Observable<number> {
  return model(spec, { density: options.density, g: options.g }, { volume: options.volume });
}
