// physics.circular_speed: the speed of a satellite in a circular orbit of radius r about a central mass M, v = sqrt(G M / r) (Gravitation: the orbital speed of a satellite). The radius is measured from the
// CENTRE of the central body, in kilometres; the mass is in kilograms; the speed comes out in kilometres per second. G is fixed here (6.674e-11 N m2/kg2), so a page cannot change it.
// UNVERIFIED until the corpus is loaded (P2); the citation pointers name the textbook pages to find.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

/** The gravitational constant, N m2 / kg2. */
export const G = 6.674e-11;

export const spec: ScienceSpec = {
  id: "physics.circular_speed",
  exportName: "circularSpeed",
  inputs: { radius: { unit: "km", min: 0, exclusive: true } },
  params: { central_mass: { unit: "kg", min: 0, exclusive: true } },
  output: { unit: "km/s" },
  fn: ({ radius, central_mass }) => Math.sqrt((G * (central_mass as number)) / ((radius as number) * 1000)) / 1000,
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Worked by hand: G M = 6.674e-11 x 5.972e24 = 3.986e14; divide by r in metres, take the square root, then to km/s.
  reference: [
    { args: { radius: 6371, central_mass: 5.972e24 }, expected: 7.9095, tolerance: 5e-4, derivation: "sqrt(3.986e14 / 6.371e6) = sqrt(6.256e7) = 7910 m/s = 7.91 km/s at the surface of Earth" },
    { args: { radius: 42164, central_mass: 5.972e24 }, expected: 3.0746, tolerance: 5e-4, derivation: "sqrt(3.986e14 / 4.2164e7) = sqrt(9.453e6) = 3075 m/s = 3.07 km/s in a geostationary orbit" },
    { args: { radius: 6771, central_mass: 5.972e24 }, expected: 7.6723, tolerance: 5e-4, derivation: "sqrt(3.986e14 / 6.771e6) = sqrt(5.887e7) = 7672 m/s, a low orbit 400 km up" },
    { args: { radius: 1000, central_mass: 1e22 }, expected: 0.8169, tolerance: 5e-4, derivation: "sqrt(6.674e-11 x 1e22 / 1e6) = sqrt(6.674e5) = 817 m/s" },
    { args: { radius: 384400, central_mass: 5.972e24 }, expected: 1.0183, tolerance: 5e-4, derivation: "sqrt(3.986e14 / 3.844e8) = sqrt(1.0369e6) = 1018 m/s at the distance of the Moon" },
    { args: { radius: 6371, central_mass: 6.417e23 }, expected: 2.5927, tolerance: 5e-4, derivation: "sqrt(6.674e-11 x 6.417e23 / 6.371e6) = sqrt(6.722e6) = 2593 m/s" },
  ],
  properties: [{ kind: "finite" }, { kind: "non_negative" }, { kind: "decreasing", arg: "radius" }, { kind: "increasing", arg: "central_mass" }, { kind: "homogeneous", arg: "radius", degree: -0.5 }, { kind: "homogeneous", arg: "central_mass", degree: 0.5 }],
  grid: { radius: [1000, 6371, 6771, 42164], central_mass: [1e22, 5.972e24, 1.989e30] },
};

export function circularSpeed(options: { radius: Observable<number>; central_mass: number }): Observable<number> {
  return model(spec, { central_mass: options.central_mass }, { radius: options.radius });
}
