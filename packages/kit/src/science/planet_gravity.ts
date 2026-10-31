// physics.planet_gravity: the gravitational acceleration on the surface of a planet of the Solar System, g = G M / R^2 (Gravitation: the textbook uses this formula to compare
// the gravitational acceleration of the planets). The input is the planet's place from the Sun (1 Mercury, 2 Venus, 3 Earth, 4 Mars, 5 Jupiter, 6 Saturn, 7 Uranus, 8 Neptune), a
// whole number; the output is in N/kg (the same as m/s2). Each planet's mass and equatorial radius are fixed here, from the NASA planetary fact sheet, so a page cannot change them.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { G } from "./circular_speed";
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

/** Mass in kg and equatorial radius in km, in order from the Sun (NASA planetary fact sheet). */
export const PLANET_DATA: readonly { mass: number; radius: number }[] = [
  { mass: 3.3011e23, radius: 2439.7 },
  { mass: 4.8675e24, radius: 6051.8 },
  { mass: 5.9724e24, radius: 6378.1 },
  { mass: 6.4171e23, radius: 3396.2 },
  { mass: 1.89819e27, radius: 71492 },
  { mass: 5.6834e26, radius: 60268 },
  { mass: 8.6813e25, radius: 25559 },
  { mass: 1.02413e26, radius: 24764 },
];

export const spec: ScienceSpec = {
  id: "physics.planet_gravity",
  exportName: "planetGravity",
  inputs: { planet: { unit: "planet", min: 1, max: 8 } },
  params: {},
  output: { unit: "N/kg" },
  fn: ({ planet }) => {
    const p = PLANET_DATA[Math.round(planet as number) - 1] as { mass: number; radius: number };
    const r = p.radius * 1000;
    return (G * p.mass) / (r * r);
  },
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from g = G M / R^2 with G = 6.674e-11: multiply G by the mass, square the radius in metres, divide.
  reference: [
    { args: { planet: 1 }, expected: 3.7014, tolerance: 2e-3, derivation: "Mercury: 6.674e-11 x 3.3011e23 = 2.2032e13; 2.4397e6 squared = 5.9521e12; 2.2032e13 / 5.9521e12 = 3.70 N/kg" },
    { args: { planet: 3 }, expected: 9.7983, tolerance: 2e-3, derivation: "Earth: 6.674e-11 x 5.9724e24 = 3.9860e14; 6.3781e6 squared = 4.0680e13; quotient 9.80 N/kg" },
    { args: { planet: 4 }, expected: 3.7131, tolerance: 2e-3, derivation: "Mars: 6.674e-11 x 6.4171e23 = 4.2828e13; 3.3962e6 squared = 1.1534e13; quotient 3.71 N/kg" },
    { args: { planet: 5 }, expected: 24.786, tolerance: 5e-3, derivation: "Jupiter: 6.674e-11 x 1.89819e27 = 1.2669e17; 7.1492e7 squared = 5.1111e15; quotient 24.79 N/kg" },
    { args: { planet: 6 }, expected: 10.443, tolerance: 5e-3, derivation: "Saturn: 6.674e-11 x 5.6834e26 = 3.7931e16; 6.0268e7 squared = 3.6322e15; quotient 10.44 N/kg" },
    { args: { planet: 8 }, expected: 11.146, tolerance: 5e-3, derivation: "Neptune: 6.674e-11 x 1.02413e26 = 6.8350e15; 2.4764e7 squared = 6.1326e14; quotient 11.15 N/kg" },
  ],
  properties: [{ kind: "finite" }, { kind: "non_negative" }],
  grid: { planet: [1, 2, 3, 4, 5, 6, 7, 8] },
};

export function planetGravity(options: { planet: Observable<number> }): Observable<number> {
  return model(spec, {}, { planet: options.planet });
}
