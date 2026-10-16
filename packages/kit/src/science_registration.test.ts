import { describe, expect, it } from "vitest";
import { HOOKES_REFERENCE, registrationFailures, type HookesFn } from "./science_registration";
import { hookesExtension } from "./science_hookes";

// Planted physics bugs. Every one of these MUST be refused by the registration suite; the real model must pass it.
// Domain guards are copied from the real model so each bug is wrong in exactly one way.
function guarded(core: HookesFn): HookesFn {
  return (load, k) => {
    if (!(k > 0)) throw new RangeError("k");
    if (!(load >= 0)) throw new RangeError("load");
    return core(load, k);
  };
}

const PLANTED: Record<string, HookesFn> = {
  "multiplies by k instead of dividing": guarded((load, k) => load * k),
  "divides by k squared": guarded((load, k) => load / (k * k)),
  "constant offset of 1 cm": guarded((load, k) => load / k + 0.01),
  "saturates above 8 N (non-physical cap)": guarded((load, k) => Math.min(load, 8) / k),
  "sign flips above 9 N": guarded((load, k) => (load > 9 ? -load / k : load / k)),
  "NaN at zero load": guarded((load, k) => (load === 0 ? Number.NaN : load / k)),
  "quadratic in load": guarded((load, k) => (load * load) / k),
  "extension grows with k": guarded((load, k) => (load * k) / 2500),
  "no domain check on k": (load, k) => load / k,
  "no domain check on load": (load, k) => {
    if (!(k > 0)) throw new RangeError("k");
    return load / k;
  },
};

describe("science registration suite for hookes", () => {
  it("accepts the real implementation", () => {
    expect(registrationFailures(hookesExtension)).toEqual([]);
  });

  it("has a hand-written derivation for every reference case", () => {
    for (const c of HOOKES_REFERENCE) expect(c.derivation.length).toBeGreaterThan(10);
  });

  it.each(Object.entries(PLANTED))("refuses the planted bug: %s", (_name, bug) => {
    expect(registrationFailures(bug).length).toBeGreaterThan(0);
  });

  it("reports the detection rate: every planted physics bug is detected", () => {
    const detected = Object.values(PLANTED).filter((bug) => registrationFailures(bug).length > 0).length;
    expect(`${detected}/${Object.keys(PLANTED).length}`).toBe(`${Object.keys(PLANTED).length}/${Object.keys(PLANTED).length}`);
  });
});
