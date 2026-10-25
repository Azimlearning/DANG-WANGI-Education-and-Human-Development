// physics.centripetal_acceleration: the acceleration towards the centre that keeps an object on a circle of radius r at speed v, a = v^2 / r (Circular Motion). The speed is in kilometres per second,
// the radius in kilometres, and the acceleration comes out in metres per second squared. At the circular speed of a satellite this equals the gravitational pull at that radius.
// UNVERIFIED until the corpus is loaded (P2); the citation pointers name the textbook pages to find.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.centripetal_acceleration",
  exportName: "centripetalAcceleration",
  inputs: { speed: { unit: "km/s", min: 0 }, radius: { unit: "km", min: 0, exclusive: true } },
  params: {},
  output: { unit: "m/s2" },
  fn: ({ speed, radius }) => ((speed as number) * 1000) ** 2 / ((radius as number) * 1000),
  citation: "UNVERIFIED (corpus not loaded until P2)",
  // Worked by hand: convert both to metres, square the speed in m/s, divide by the radius in metres.
  reference: [
    { args: { speed: 7.9095, radius: 6371 }, expected: 9.8195, tolerance: 5e-4, derivation: "(7909.5 m/s)^2 / 6.371e6 m = 6.2562e7 / 6.371e6 = 9.82 m/s2, close to g at the surface" },
    { args: { speed: 1, radius: 1000 }, expected: 1, tolerance: 1e-9, derivation: "(1000 m/s)^2 / 1e6 m = 1e6 / 1e6 = 1 m/s2" },
    { args: { speed: 3.0746, radius: 42164 }, expected: 0.2242, tolerance: 5e-4, derivation: "(3074.6 m/s)^2 / 4.2164e7 m = 9.4528e6 / 4.2164e7 = 0.224 m/s2 in a geostationary orbit" },
    { args: { speed: 11.1857, radius: 6371 }, expected: 19.639, tolerance: 5e-3, derivation: "(11185.7 m/s)^2 / 6.371e6 m = 1.2512e8 / 6.371e6 = 19.64 m/s2, twice the circular case" },
    { args: { speed: 0, radius: 6371 }, expected: 0, tolerance: 1e-9, derivation: "an object at rest needs no centripetal acceleration" },
  ],
  properties: [{ kind: "finite" }, { kind: "non_negative" }, { kind: "increasing", arg: "speed" }, { kind: "decreasing", arg: "radius" }, { kind: "homogeneous", arg: "speed", degree: 2 }, { kind: "homogeneous", arg: "radius", degree: -1 }],
  grid: { speed: [1, 3, 7.9, 11.2, 15], radius: [1000, 6371, 42164] },
};

export function centripetalAcceleration(options: { speed: Observable<number>; radius: Observable<number> }): Observable<number> {
  return model(spec, {}, { speed: options.speed, radius: options.radius });
}
