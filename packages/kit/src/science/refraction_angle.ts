// physics.refraction_angle: the angle of refraction when light passes from air into a denser medium, from Snell's law n = sin i / sin r (Light and Optics).
// The angle of incidence i is in degrees and must be below 90; the refractive index n of the medium is at least 1 (air is 1). The angle of refraction r comes out in degrees.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.refraction_angle",
  exportName: "refractionAngle",
  inputs: { incidence_angle: { unit: "deg", min: 0, max: 90, maxExclusive: true }, refractive_index: { unit: "ratio", min: 1 } },
  params: {},
  output: { unit: "deg" },
  fn: ({ incidence_angle, refractive_index }) => (Math.asin(Math.sin(((incidence_angle as number) * Math.PI) / 180) / (refractive_index as number)) * 180) / Math.PI,
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from sin r = sin i / n. The first three use angles whose sines are exact: sin 45 = sqrt(2)/2, sin 60 = sqrt(3)/2, sin 30 = 1/2.
  reference: [
    { args: { incidence_angle: 45, refractive_index: 1.4142135624 }, expected: 30, tolerance: 1e-6, derivation: "sin r = (sqrt2 / 2) / sqrt2 = 1/2, so r = 30 degrees" },
    { args: { incidence_angle: 60, refractive_index: 1.7320508076 }, expected: 30, tolerance: 1e-6, derivation: "sin r = (sqrt3 / 2) / sqrt3 = 1/2, so r = 30 degrees" },
    { args: { incidence_angle: 30, refractive_index: 1 }, expected: 30, tolerance: 1e-9, derivation: "n = 1 (air to air): sin r = sin 30, so the ray does not bend" },
    { args: { incidence_angle: 0, refractive_index: 1.5 }, expected: 0, tolerance: 1e-9, derivation: "along the normal: sin r = 0, so r = 0" },
    { args: { incidence_angle: 30, refractive_index: 1.5 }, expected: 19.4712, tolerance: 5e-4, derivation: "sin r = 0.5 / 1.5 = 1/3 = 0.33333; r = inverse sine of 1/3 = 19.47 degrees" },
    { args: { incidence_angle: 30, refractive_index: 2 }, expected: 14.4775, tolerance: 5e-4, derivation: "sin r = 0.5 / 2 = 0.25; r = inverse sine of 0.25 = 14.48 degrees" },
    { args: { incidence_angle: 45, refractive_index: 1.33 }, expected: 32.1176, tolerance: 5e-4, derivation: "sin r = 0.70711 / 1.33 = 0.53166; r = 32.12 degrees (air to water)" },
    { args: { incidence_angle: 80, refractive_index: 2.42 }, expected: 24.0131, tolerance: 5e-4, derivation: "sin r = 0.98481 / 2.42 = 0.40694; r = 24.01 degrees (air to diamond)" },
  ],
  properties: [{ kind: "finite" }, { kind: "non_negative" }, { kind: "increasing", arg: "incidence_angle" }, { kind: "decreasing", arg: "refractive_index" }],
  grid: { incidence_angle: [10, 30, 45, 60, 85], refractive_index: [1, 1.33, 1.5, 2.42] },
};

export function refractionAngle(options: { incidence_angle: Observable<number>; refractive_index: Observable<number> }): Observable<number> {
  return model(spec, {}, { incidence_angle: options.incidence_angle, refractive_index: options.refractive_index });
}
