// physics.half_life_decay: what is left of a radioactive sample after a time, N = N0 x (1/2)^(t / T) (Nuclear Physics: half-life). Time and half-life are in the same unit
// (minutes here); the initial amount N0 is a number of undecayed nuclei or an activity in any one unit, and the answer is in that unit. The textbook states the rule for a
// whole number of half-lives; an Environment keeps the time control on whole multiples of the half-life, so what it shows is what the book states.
// The Kit holds no textbook text. The citations that support this model are pointers in data/citations/pointers.json, which each Plan names and the verifier re-proves.
import { model } from "./model";
import type { ScienceSpec } from "./spec";
import type { Observable } from "../observable";

export const spec: ScienceSpec = {
  id: "physics.half_life_decay",
  exportName: "halfLifeDecay",
  inputs: { time: { unit: "min", min: 0 } },
  params: { half_life: { unit: "min", min: 0, exclusive: true }, initial: { unit: "/s", min: 0, exclusive: true } },
  output: { unit: "/s" },
  fn: ({ time, half_life, initial }) => (initial as number) * 0.5 ** ((time as number) / (half_life as number)),
  citation: "UNVERIFIED (the Kit holds no textbook text; a Plan's citations decide its label)",
  // Worked by hand from N = N0 / 2^n with n = t / T. The first is the textbook's worked example (480 per second, half-life 6 minutes, after 30 minutes).
  reference: [
    { args: { time: 30, half_life: 6, initial: 480 }, expected: 15, tolerance: 1e-9, derivation: "n = 30 / 6 = 5 half-lives; 480 / 2^5 = 480 / 32 = 15 per second" },
    { args: { time: 20, half_life: 10, initial: 100 }, expected: 25, tolerance: 1e-9, derivation: "n = 2; 100 / 4 = 25, which is 25% of the start" },
    { args: { time: 0, half_life: 8, initial: 64 }, expected: 64, tolerance: 1e-9, derivation: "no time has passed, so all of it is left" },
    { args: { time: 10, half_life: 10, initial: 100 }, expected: 50, tolerance: 1e-9, derivation: "one half-life leaves half" },
    { args: { time: 24, half_life: 8, initial: 800 }, expected: 100, tolerance: 1e-9, derivation: "n = 3; 800 / 8 = 100" },
    { args: { time: 40, half_life: 10, initial: 1600 }, expected: 100, tolerance: 1e-9, derivation: "n = 4; 1 600 / 16 = 100" },
  ],
  properties: [
    { kind: "finite" },
    { kind: "non_negative" },
    { kind: "decreasing", arg: "time" },
    { kind: "increasing", arg: "half_life" },
    { kind: "increasing", arg: "initial" },
    { kind: "homogeneous", arg: "initial", degree: 1 },
  ],
  grid: { time: [4, 10, 20, 40], half_life: [5, 10], initial: [64, 100, 480] },
};

export function halfLifeDecay(options: { time: Observable<number>; half_life: number; initial: number }): Observable<number> {
  return model(spec, { half_life: options.half_life, initial: options.initial }, { time: options.time });
}
