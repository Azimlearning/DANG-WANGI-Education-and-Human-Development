// physics.critical_angle: the smallest angle of incidence at which light inside a medium is totally internally reflected at its boundary with air, sin c = 1 / n
// (Light and Optics: total internal reflection). The refractive index n of the medium is at least 1; the critical angle comes out in degrees (n = 1 gives 90).
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.critical_angle",
  exportName: "criticalAngle",
  inputs: { refractive_index: { unit: "ratio", min: 1 } },
  params: {},
  output: { unit: "deg" },
  fn: ({ refractive_index }) => (Math.asin(1 / (refractive_index as number)) * 180) / Math.PI,
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from sin c = 1 / n. Sines with exact values: sin 90 = 1, sin 45 = sqrt(2)/2, sin 30 = 1/2.
  reference: [
    { args: { refractive_index: 1 }, expected: 90, tolerance: 1e-9, derivation: "sin c = 1, so c = 90 degrees (no bending, no total internal reflection)" },
    { args: { refractive_index: 1.4142135624 }, expected: 45, tolerance: 1e-6, derivation: "sin c = 1 / sqrt2 = sqrt2 / 2, so c = 45 degrees" },
    { args: { refractive_index: 2 }, expected: 30, tolerance: 1e-9, derivation: "sin c = 1/2, so c = 30 degrees" },
    { args: { refractive_index: 1.49 }, expected: 42.1552, tolerance: 5e-4, derivation: "sin c = 1 / 1.49 = 0.67114; c = 42.16 degrees (the glass prism of a worked example)" },
    { args: { refractive_index: 1.5 }, expected: 41.8103, tolerance: 5e-4, derivation: "sin c = 1 / 1.5 = 0.66667; c = 41.81 degrees (glass)" },
    { args: { refractive_index: 1.33 }, expected: 48.7535, tolerance: 5e-4, derivation: "sin c = 1 / 1.33 = 0.75188; c = 48.75 degrees (water)" },
    { args: { refractive_index: 2.42 }, expected: 24.4075, tolerance: 5e-4, derivation: "sin c = 1 / 2.42 = 0.41322; c = 24.41 degrees (diamond)" },
  ],
  properties: [{ kind: "finite" }, { kind: "non_negative" }, { kind: "decreasing", arg: "refractive_index" }],
  grid: { refractive_index: [1, 1.33, 1.49, 1.5, 2.42] },
};

export function criticalAngle(options: { refractive_index: Observable<number> }): Observable<number> {
  return model(spec, {}, { refractive_index: options.refractive_index });
}
