// physics.weight: the weight of a mass in a gravitational field, W = m g (Gravitation: the gravitational force on an object at the surface of a planet). Mass in kg, the
// gravitational field strength in N/kg; the weight comes out in newtons.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.weight",
  exportName: "weight",
  inputs: { mass: { unit: "kg", min: 0 }, gravity: { unit: "N/kg", min: 0 } },
  params: {},
  output: { unit: "N" },
  fn: ({ mass, gravity }) => (mass as number) * (gravity as number),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from W = m g.
  reference: [
    { args: { mass: 1, gravity: 9.81 }, expected: 9.81, tolerance: 1e-9, derivation: "1 kg x 9.81 N/kg = 9.81 N on Earth" },
    { args: { mass: 5, gravity: 3.7 }, expected: 18.5, tolerance: 1e-9, derivation: "5 x 3.7 = 18.5 N on Mars" },
    { args: { mass: 2, gravity: 24.79 }, expected: 49.58, tolerance: 1e-9, derivation: "2 x 24.79 = 49.58 N on Jupiter" },
    { args: { mass: 0, gravity: 9.81 }, expected: 0, tolerance: 1e-12, derivation: "no mass has no weight" },
    { args: { mass: 60, gravity: 1.62 }, expected: 97.2, tolerance: 1e-9, derivation: "60 x 1.62 = 97.2 N, a 60 kg astronaut on the Moon" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "increasing", arg: "mass" },
    { kind: "increasing", arg: "gravity" },
    { kind: "homogeneous", arg: "mass", degree: 1 },
    { kind: "homogeneous", arg: "gravity", degree: 1 },
  ],
  grid: { mass: [0.5, 1, 2, 60], gravity: [1.62, 3.7, 9.81, 24.79] },
};

export function weight(options: { mass: Observable<number>; gravity: Observable<number> }): Observable<number> {
  return model(spec, {}, { mass: options.mass, gravity: options.gravity });
}
