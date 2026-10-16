import { describe, expect, it } from "vitest";
import { spec as average } from "./average_rate";
import { spec as dilution } from "./dilution";
import { spec as heat } from "./heat_energy";
import { spec as magnification } from "./magnification";
import { spec as moles } from "./moles";
import { spec as photo } from "./photosynthesis";
import { spec as sa } from "./sa_to_v";
import { spec as titration } from "./titration";
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
  {
    spec: magnification,
    bugs: {
      "multiplies image by actual": planted(magnification, (a) => n(a, "image") * n(a, "actual")),
      "divides actual by image": planted(magnification, (a) => n(a, "actual") / Math.max(n(a, "image"), 1e-9)),
      "off by a factor of 10": planted(magnification, (a) => (n(a, "image") / n(a, "actual")) * 10),
      "millimetres treated as micrometres": planted(magnification, (a) => (n(a, "image") / n(a, "actual")) / 1000),
      "caps at 1000 times": planted(magnification, (a) => Math.min(n(a, "image") / n(a, "actual"), 1000)),
      "sign flips above 60 mm": planted(magnification, (a) => (n(a, "image") > 60 ? -1 : 1) * (n(a, "image") / n(a, "actual"))),
      "NaN with no image": planted(magnification, (a) => (n(a, "image") === 0 ? Number.NaN : n(a, "image") / n(a, "actual"))),
      "squares the ratio (area, not length)": planted(magnification, (a) => (n(a, "image") / n(a, "actual")) ** 2),
      "rounds to tens": planted(magnification, (a) => Math.round(n(a, "image") / n(a, "actual") / 10) * 10),
      "no domain check on actual": planted(magnification, (a) => n(a, "image") / n(a, "actual"), ["actual"]),
      "no domain check on image": planted(magnification, (a) => n(a, "image") / n(a, "actual"), ["image"]),
    },
  },
  {
    spec: sa,
    bugs: {
      "multiplies by the side": planted(sa, (a) => 6 * n(a, "side")),
      "counts four faces": planted(sa, (a) => 4 / n(a, "side")),
      "counts three faces": planted(sa, (a) => 3 / n(a, "side")),
      "area over area": planted(sa, (a) => 6 / n(a, "side") ** 2),
      "volume over area": planted(sa, (a) => n(a, "side") / 6),
      "forgets the six": planted(sa, (a) => 1 / n(a, "side")),
      "caps at 6": planted(sa, (a) => Math.min(6 / n(a, "side"), 6)),
      "NaN at side 3": planted(sa, (a) => (n(a, "side") === 3 ? Number.NaN : 6 / n(a, "side"))),
      "sign flips above 5 cm": planted(sa, (a) => (n(a, "side") > 5 ? -1 : 1) * (6 / n(a, "side"))),
      "rounds to a whole number": planted(sa, (a) => Math.round(6 / n(a, "side"))),
      "no domain check on side": planted(sa, (a) => 6 / n(a, "side"), ["side"]),
    },
  },
  {
    spec: photo,
    bugs: {
      "adds respiration instead of subtracting": planted(photo, (a) => (n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light")) + n(a, "resp")),
      "forgets respiration": planted(photo, (a) => (n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light"))),
      "linear instead of saturating": planted(photo, (a) => (n(a, "pmax") * n(a, "light")) / n(a, "k") - n(a, "resp")),
      "k and light swapped": planted(photo, (a) => (n(a, "pmax") * n(a, "k")) / (n(a, "k") + n(a, "light")) - n(a, "resp")),
      "pmax ignored": planted(photo, (a) => n(a, "light") / (n(a, "k") + n(a, "light")) - n(a, "resp")),
      "caps net uptake at 4": planted(photo, (a) => Math.min((n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light")) - n(a, "resp"), 4)),
      "clamps below zero (hides the compensation point)": planted(photo, (a) => Math.max((n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light")) - n(a, "resp"), 0)),
      "NaN with no light": planted(photo, (a) => (n(a, "light") === 0 ? Number.NaN : (n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light")) - n(a, "resp"))),
      "respiration doubled": planted(photo, (a) => (n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light")) - 2 * n(a, "resp")),
      "no domain check on k": planted(photo, (a) => (n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light")) - n(a, "resp"), ["k"]),
      "no domain check on light": planted(photo, (a) => (n(a, "pmax") * n(a, "light")) / (n(a, "k") + n(a, "light")) - n(a, "resp"), ["light"]),
    },
  },
  {
    spec: moles,
    bugs: {
      "multiplies by molar mass": planted(moles, (a) => n(a, "mass") * n(a, "molar_mass")),
      "divides molar mass by mass": planted(moles, (a) => n(a, "molar_mass") / Math.max(n(a, "mass"), 1e-9)),
      "uses 22.4 as the divisor": planted(moles, (a) => n(a, "mass") / 22.4),
      "kilograms treated as grams": planted(moles, (a) => n(a, "mass") / n(a, "molar_mass") / 1000),
      "off by Avogadro's constant": planted(moles, (a) => (n(a, "mass") / n(a, "molar_mass")) * 6.02e23),
      "caps at 5 mol": planted(moles, (a) => Math.min(n(a, "mass") / n(a, "molar_mass"), 5)),
      "sign flips above 50 g": planted(moles, (a) => (n(a, "mass") > 50 ? -1 : 1) * (n(a, "mass") / n(a, "molar_mass"))),
      "NaN with no mass": planted(moles, (a) => (n(a, "mass") === 0 ? Number.NaN : n(a, "mass") / n(a, "molar_mass"))),
      "rounds to a whole mole": planted(moles, (a) => Math.round(n(a, "mass") / n(a, "molar_mass"))),
      "no domain check on molar mass": planted(moles, (a) => n(a, "mass") / n(a, "molar_mass"), ["molar_mass"]),
      "no domain check on mass": planted(moles, (a) => n(a, "mass") / n(a, "molar_mass"), ["mass"]),
    },
  },
  {
    spec: titration,
    bugs: {
      "coefficients inverted": planted(titration, (a) => (n(a, "ma") * n(a, "va") * n(a, "acid_coeff")) / (n(a, "base_coeff") * n(a, "vb"))),
      "coefficients ignored": planted(titration, (a) => (n(a, "ma") * n(a, "va")) / n(a, "vb")),
      "volumes swapped": planted(titration, (a) => (n(a, "ma") * n(a, "vb") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "va"))),
      "multiplies by vb": planted(titration, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff") * n(a, "vb")) / n(a, "acid_coeff")),
      "forgets the acid concentration": planted(titration, (a) => (n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "vb"))),
      "cm3 and dm3 mixed up": planted(titration, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "vb")) / 1000),
      "caps at 0.5": planted(titration, (a) => Math.min((n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "vb")), 0.5)),
      "sign flips above 30 cm3": planted(titration, (a) => (n(a, "vb") > 30 ? -1 : 1) * ((n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "vb")))),
      "NaN at 25 cm3 of acid": planted(titration, (a) => (n(a, "va") === 25 ? Number.NaN : (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "vb")))),
      "no domain check on vb": planted(titration, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "vb")), ["vb"]),
      "no domain check on acid coefficient": planted(titration, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "vb")), ["acid_coeff"]),
    },
  },
  {
    spec: dilution,
    bugs: {
      "multiplies by v2": planted(dilution, (a) => (n(a, "m1") * n(a, "v1") * n(a, "v2")) / 100),
      "v1 and v2 swapped": planted(dilution, (a) => (n(a, "m1") * n(a, "v2")) / n(a, "v1")),
      "forgets v1": planted(dilution, (a) => n(a, "m1") / n(a, "v2")),
      "forgets the starting concentration": planted(dilution, (a) => n(a, "v1") / n(a, "v2")),
      "subtracts instead of dividing": planted(dilution, (a) => n(a, "m1") - n(a, "v2") / 100),
      "uses added water as the volume": planted(dilution, (a) => (n(a, "m1") * n(a, "v1")) / Math.max(n(a, "v2") - n(a, "v1"), 1e-9)),
      "caps at 1": planted(dilution, (a) => Math.min((n(a, "m1") * n(a, "v1")) / n(a, "v2"), 1)),
      "sign flips above 80 cm3": planted(dilution, (a) => (n(a, "v2") > 80 ? -1 : 1) * ((n(a, "m1") * n(a, "v1")) / n(a, "v2"))),
      "NaN at 25 cm3": planted(dilution, (a) => (n(a, "v2") === 25 ? Number.NaN : (n(a, "m1") * n(a, "v1")) / n(a, "v2"))),
      "no domain check on v2": planted(dilution, (a) => (n(a, "m1") * n(a, "v1")) / n(a, "v2"), ["v2"]),
      "no domain check on m1": planted(dilution, (a) => (n(a, "m1") * n(a, "v1")) / n(a, "v2"), ["m1"]),
    },
  },
  {
    spec: heat,
    bugs: {
      "forgets the specific heat capacity": planted(heat, (a) => n(a, "mass") * n(a, "delta_t")),
      "forgets the mass": planted(heat, (a) => n(a, "c") * n(a, "delta_t")),
      "adds instead of multiplying": planted(heat, (a) => n(a, "mass") + n(a, "c") + n(a, "delta_t")),
      "kilojoules reported as joules": planted(heat, (a) => (n(a, "mass") * n(a, "c") * n(a, "delta_t")) / 1000),
      "squares the temperature change": planted(heat, (a) => n(a, "mass") * n(a, "c") * n(a, "delta_t") ** 2),
      "uses 4.18 whatever c is": planted(heat, (a) => n(a, "mass") * 4.18 * n(a, "delta_t")),
      "caps at 5000 J": planted(heat, (a) => Math.min(n(a, "mass") * n(a, "c") * n(a, "delta_t"), 5000)),
      "sign flips above 8 degrees": planted(heat, (a) => (n(a, "delta_t") > 8 ? -1 : 1) * (n(a, "mass") * n(a, "c") * n(a, "delta_t"))),
      "NaN with no change": planted(heat, (a) => (n(a, "delta_t") === 0 ? Number.NaN : n(a, "mass") * n(a, "c") * n(a, "delta_t"))),
      "no domain check on mass": planted(heat, (a) => n(a, "mass") * n(a, "c") * n(a, "delta_t"), ["mass"]),
      "no domain check on delta T": planted(heat, (a) => n(a, "mass") * n(a, "c") * n(a, "delta_t"), ["delta_t"]),
    },
  },
  {
    spec: average,
    bugs: {
      "multiplies volume by time": planted(average, (a) => n(a, "volume") * n(a, "time")),
      "divides time by volume": planted(average, (a) => n(a, "time") / Math.max(n(a, "volume"), 1e-9)),
      "minutes treated as seconds": planted(average, (a) => (n(a, "volume") / n(a, "time")) * 60),
      "uses half the time": planted(average, (a) => n(a, "volume") / (n(a, "time") / 2)),
      "caps at 2": planted(average, (a) => Math.min(n(a, "volume") / n(a, "time"), 2)),
      "sign flips above 40 cm3": planted(average, (a) => (n(a, "volume") > 40 ? -1 : 1) * (n(a, "volume") / n(a, "time"))),
      "NaN with no gas": planted(average, (a) => (n(a, "volume") === 0 ? Number.NaN : n(a, "volume") / n(a, "time"))),
      "rounds to whole numbers": planted(average, (a) => Math.round(n(a, "volume") / n(a, "time"))),
      "no domain check on time": planted(average, (a) => n(a, "volume") / n(a, "time"), ["time"]),
      "no domain check on volume": planted(average, (a) => n(a, "volume") / n(a, "time"), ["volume"]),
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
