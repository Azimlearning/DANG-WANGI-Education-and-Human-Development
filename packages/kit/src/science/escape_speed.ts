// physics.escape_speed: the speed that lets an object leave a central mass for good, v = sqrt(2 G M / r) (Gravitation: escape velocity). The radius is measured from the CENTRE of the central body, in
// kilometres; the mass is in kilograms; the speed comes out in kilometres per second. It is the square root of 2 times the circular speed at the same radius, which a test checks. G is fixed here.
// UNVERIFIED until the corpus is loaded (P2); the citation pointers name the textbook pages to find.
import { G } from "./circular_speed";
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.escape_speed",
  exportName: "escapeSpeed",
  inputs: { radius: { unit: "km", min: 0, exclusive: true } },
  params: { central_mass: { unit: "kg", min: 0, exclusive: true } },
  output: { unit: "km/s" },
  fn: ({ radius, central_mass }) => Math.sqrt((2 * G * (central_mass as number)) / ((radius as number) * 1000)) / 1000,
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand: 2 G M = 7.971e14; divide by r in metres, take the square root, then to km/s.
  reference: [
    { args: { radius: 6371, central_mass: 5.972e24 }, expected: 11.1857, tolerance: 5e-4, derivation: "sqrt(7.971e14 / 6.371e6) = sqrt(1.251e8) = 11 186 m/s = 11.2 km/s from the surface of Earth" },
    { args: { radius: 42164, central_mass: 5.972e24 }, expected: 4.3481, tolerance: 5e-4, derivation: "sqrt(7.971e14 / 4.2164e7) = sqrt(1.890e7) = 4348 m/s" },
    { args: { radius: 6771, central_mass: 5.972e24 }, expected: 10.8503, tolerance: 5e-4, derivation: "sqrt(7.971e14 / 6.771e6) = sqrt(1.1773e8) = 10 850 m/s from a low orbit 400 km up" },
    { args: { radius: 384400, central_mass: 5.972e24 }, expected: 1.4400, tolerance: 5e-4, derivation: "sqrt(7.971e14 / 3.844e8) = sqrt(2.0737e6) = 1440 m/s at the distance of the Moon" },
    { args: { radius: 6371, central_mass: 6.417e23 }, expected: 3.6667, tolerance: 5e-4, derivation: "sqrt(2 x 6.674e-11 x 6.417e23 / 6.371e6) = sqrt(1.3444e7) = 3667 m/s" },
    { args: { radius: 1000, central_mass: 1e22 }, expected: 1.1553, tolerance: 5e-4, derivation: "sqrt(2 x 6.674e-11 x 1e22 / 1e6) = sqrt(1.335e6) = 1155 m/s" },
  ],
  properties: [{ kind: "finite" }, { kind: "non_negative" }, { kind: "decreasing", arg: "radius" }, { kind: "increasing", arg: "central_mass" }, { kind: "homogeneous", arg: "radius", degree: -0.5 }, { kind: "homogeneous", arg: "central_mass", degree: 0.5 }],
  grid: { radius: [1000, 6371, 6771, 42164], central_mass: [1e22, 5.972e24, 1.989e30] },
};

export function escapeSpeed(options: { radius: Observable<number>; central_mass: number }): Observable<number> {
  return model(spec, { central_mass: options.central_mass }, { radius: options.radius });
}
