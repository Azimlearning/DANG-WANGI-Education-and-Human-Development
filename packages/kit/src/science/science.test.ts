import { describe, expect, it } from "vitest";
import { spec as hookes } from "./hookes";
import { spec as ohm } from "./ohm";
import { spec as pressure } from "./pressure_depth";
import { domainErrors, guarded, registrationFailures, type Impl, type ScienceSpec } from "./spec";

// A planted physics bug: a function that is wrong in exactly one way. Its domain guard is the real one unless a test skips an argument's
// check on purpose (the "no domain check" bugs).
function planted(spec: ScienceSpec, core: Impl, skipDomain: string[] = []): Impl {
  return (args) => {
    const errors = domainErrors(spec, args).filter((e) => !skipDomain.some((n) => e.startsWith(`${n} `)));
    if (errors.length > 0) throw new RangeError(errors.join("; "));
    return core(args);
  };
}

const n = (a: Record<string, number>, k: string) => a[k] as number;

const BUGS: { spec: ScienceSpec; bugs: Record<string, Impl> }[] = [
  {
    spec: hookes,
    bugs: {
      "multiplies by k instead of dividing": planted(hookes, (a) => n(a, "load") * n(a, "k")),
      "divides by k squared": planted(hookes, (a) => n(a, "load") / (n(a, "k") * n(a, "k"))),
      "constant offset of 1 cm": planted(hookes, (a) => n(a, "load") / n(a, "k") + 0.01),
      "saturates above 8 N": planted(hookes, (a) => Math.min(n(a, "load"), 8) / n(a, "k")),
      "sign flips above 9 N": planted(hookes, (a) => (n(a, "load") > 9 ? -n(a, "load") : n(a, "load")) / n(a, "k")),
      "NaN at zero load": planted(hookes, (a) => (n(a, "load") === 0 ? Number.NaN : n(a, "load") / n(a, "k"))),
      "quadratic in load": planted(hookes, (a) => (n(a, "load") * n(a, "load")) / n(a, "k")),
      "extension grows with k": planted(hookes, (a) => (n(a, "load") * n(a, "k")) / 2500),
      "no domain check on k": planted(hookes, (a) => n(a, "load") / n(a, "k"), ["k"]),
      "no domain check on load": planted(hookes, (a) => n(a, "load") / n(a, "k"), ["load"]),
      "rounds to a whole centimetre": planted(hookes, (a) => Math.round((n(a, "load") / n(a, "k")) * 100) / 100),
    },
  },
  {
    spec: ohm,
    bugs: {
      "multiplies V by R": planted(ohm, (a) => n(a, "voltage") * n(a, "resistance")),
      "divides R by V": planted(ohm, (a) => n(a, "resistance") / n(a, "voltage")),
      "adds 1 ohm of hidden resistance": planted(ohm, (a) => n(a, "voltage") / (n(a, "resistance") + 1)),
      "caps current at 10 A": planted(ohm, (a) => Math.min(n(a, "voltage") / n(a, "resistance"), 10)),
      "sign flips above 200 V": planted(ohm, (a) => (n(a, "voltage") > 200 ? -1 : 1) * (n(a, "voltage") / n(a, "resistance"))),
      "NaN at zero voltage": planted(ohm, (a) => (n(a, "voltage") === 0 ? Number.NaN : n(a, "voltage") / n(a, "resistance"))),
      "V squared over R (power, not current)": planted(ohm, (a) => (n(a, "voltage") ** 2) / n(a, "resistance")),
      "divides by R squared": planted(ohm, (a) => n(a, "voltage") / n(a, "resistance") ** 2),
      "milliamps reported as amps": planted(ohm, (a) => (n(a, "voltage") / n(a, "resistance")) * 1000),
      "truncates to whole amps": planted(ohm, (a) => Math.floor(n(a, "voltage") / n(a, "resistance"))),
      "no domain check on R": planted(ohm, (a) => n(a, "voltage") / n(a, "resistance"), ["resistance"]),
      "no domain check on V": planted(ohm, (a) => n(a, "voltage") / n(a, "resistance"), ["voltage"]),
    },
  },
  {
    spec: pressure,
    bugs: {
      "forgets g": planted(pressure, (a) => n(a, "depth") * n(a, "density")),
      "forgets density": planted(pressure, (a) => n(a, "depth") * n(a, "g")),
      "doubles the result": planted(pressure, (a) => 2 * n(a, "depth") * n(a, "density") * n(a, "g")),
      "ignores the g parameter and uses 9.8": planted(pressure, (a) => n(a, "depth") * n(a, "density") * 9.8),
      "caps depth at 8 m": planted(pressure, (a) => Math.min(n(a, "depth"), 8) * n(a, "density") * n(a, "g")),
      "divides by density": planted(pressure, (a) => (n(a, "depth") * n(a, "g")) / n(a, "density")),
      "sign flips above 9 m": planted(pressure, (a) => (n(a, "depth") > 9 ? -1 : 1) * n(a, "depth") * n(a, "density") * n(a, "g")),
      "NaN at the surface": planted(pressure, (a) => (n(a, "depth") === 0 ? Number.NaN : n(a, "depth") * n(a, "density") * n(a, "g"))),
      "quadratic in depth": planted(pressure, (a) => n(a, "depth") ** 2 * n(a, "density") * n(a, "g")),
      "adds atmospheric pressure (absolute, not gauge)": planted(pressure, (a) => n(a, "depth") * n(a, "density") * n(a, "g") + 101325),
      "kilopascals reported as pascals": planted(pressure, (a) => (n(a, "depth") * n(a, "density") * n(a, "g")) / 1000),
      "no domain check on density": planted(pressure, (a) => n(a, "depth") * n(a, "density") * n(a, "g"), ["density"]),
      "no domain check on depth": planted(pressure, (a) => n(a, "depth") * n(a, "density") * n(a, "g"), ["depth"]),
    },
  },
];

describe.each(BUGS)("registration suite for $spec.id", ({ spec, bugs }) => {
  it("accepts the real implementation", () => {
    expect(registrationFailures(spec, guarded(spec))).toEqual([]);
  });

  it("has a written citation status, units, a domain and a derivation for every reference case", () => {
    expect(spec.citation).toMatch(/^UNVERIFIED/);
    expect(Object.values({ ...spec.inputs, ...spec.params }).every((q) => q.unit.length > 0)).toBe(true);
    expect(spec.output.unit.length).toBeGreaterThan(0);
    expect(spec.reference.length).toBeGreaterThanOrEqual(5);
    for (const c of spec.reference) expect(c.derivation.length).toBeGreaterThan(10);
  });

  it("has at least 8 planted bugs", () => {
    expect(Object.keys(bugs).length).toBeGreaterThanOrEqual(8);
  });

  it.each(Object.entries(bugs))("refuses the planted bug: %s", (_name, bug) => {
    expect(registrationFailures(spec, bug).length).toBeGreaterThan(0);
  });

  it("detects every planted bug (n of n)", () => {
    const detected = Object.values(bugs).filter((bug) => registrationFailures(spec, bug).length > 0).length;
    expect(`${detected}/${Object.keys(bugs).length}`).toBe(`${Object.keys(bugs).length}/${Object.keys(bugs).length}`);
  });
});

describe("domain guard", () => {
  it("refuses values outside the domain and non-numbers", () => {
    const run = guarded(hookes);
    expect(() => run({ load: -1, k: 10 })).toThrow(RangeError);
    expect(() => run({ load: 1, k: 0 })).toThrow(RangeError);
    expect(() => run({ load: Number.NaN, k: 10 })).toThrow(RangeError);
    expect(() => run({ load: Number.POSITIVE_INFINITY, k: 10 })).toThrow(RangeError);
    expect(run({ load: 10, k: 50 })).toBeCloseTo(0.2, 12);
  });
});
