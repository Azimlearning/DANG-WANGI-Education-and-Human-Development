import { describe, expect, it } from "vitest";
import { spec as average } from "./average_rate";
import { spec as dilution } from "./dilution";
import { spec as heat } from "./heat_energy";
import { spec as magnification } from "./magnification";
import { spec as moles } from "./moles";
import { spec as wave } from "./wave_speed";
import { spec as newton } from "./newton_second";
import { spec as cardiac } from "./cardiac_output";
import { spec as massChange } from "./mass_change";
import { spec as phSpec } from "./ph";
import { spec as gasVol } from "./gas_volume";
import { spec as photo } from "./photosynthesis";
import { spec as sa } from "./sa_to_v";
import { spec as titration } from "./titration";
import { spec as titrationEnd } from "./titration_endpoint";
import { spec as respiration } from "./respiration_energy";
import { G, spec as circular } from "./circular_speed";
import { spec as escape } from "./escape_speed";
import { spec as centripetal } from "./centripetal_acceleration";
import { spec as hookes } from "./hookes";
import { spec as ohm } from "./ohm";
import { spec as pressure } from "./pressure_depth";
import { spec as refraction } from "./refraction_angle";
import { spec as critical } from "./critical_angle";
import { spec as specificHeat } from "./specific_heat";
import { spec as transformer } from "./transformer";
import { spec as halfLife } from "./half_life";
import { spec as relativeAtomicMassSpec } from "./relative_atomic_mass";
import { spec as foodEnergy } from "./food_energy";
import { spec as boyle } from "./boyle_law";
import { spec as parallel } from "./parallel_resistance";
import { spec as buoyant } from "./buoyant_force";
import { spec as cellV } from "./cell_voltage";
import { spec as popDensity } from "./population_density";
import { spec as eEnergy } from "./electrical_energy";
import { PLANET_DATA, spec as planetG } from "./planet_gravity";
import { spec as weightSpec } from "./weight";
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
    spec: titrationEnd,
    bugs: {
      "coefficients inverted": planted(titrationEnd, (a) => (n(a, "ma") * n(a, "va") * n(a, "acid_coeff")) / (n(a, "base_coeff") * n(a, "mb"))),
      "coefficients ignored": planted(titrationEnd, (a) => (n(a, "ma") * n(a, "va")) / n(a, "mb")),
      "base concentration multiplied, not divided": planted(titrationEnd, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff") * n(a, "mb")) / n(a, "acid_coeff")),
      "forgets the acid concentration": planted(titrationEnd, (a) => (n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb"))),
      "forgets the acid volume": planted(titrationEnd, (a) => (n(a, "ma") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb"))),
      "cm3 and dm3 mixed up": planted(titrationEnd, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb")) / 1000),
      "caps at 30 cm3": planted(titrationEnd, (a) => Math.min((n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb")), 30)),
      "sign flips above 35 cm3": planted(titrationEnd, (a) => (n(a, "va") > 35 ? -1 : 1) * ((n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb")))),
      "NaN at 25 cm3 of acid": planted(titrationEnd, (a) => (n(a, "va") === 25 ? Number.NaN : (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb")))),
      "no domain check on mb": planted(titrationEnd, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb")), ["mb"]),
      "no domain check on acid coefficient": planted(titrationEnd, (a) => (n(a, "ma") * n(a, "va") * n(a, "base_coeff")) / (n(a, "acid_coeff") * n(a, "mb")), ["acid_coeff"]),
    },
  },
  {
    spec: respiration,
    bugs: {
      "divides by the energy per mole": planted(respiration, (a) => n(a, "glucose") / n(a, "energy_per_mole")),
      "adds instead of multiplies": planted(respiration, (a) => n(a, "glucose") + n(a, "energy_per_mole")),
      "forgets the glucose": planted(respiration, (a) => n(a, "energy_per_mole")),
      "kilojoules and joules mixed up": planted(respiration, (a) => n(a, "glucose") * n(a, "energy_per_mole") * 1000),
      "aerobic figure used for everything": planted(respiration, (a) => n(a, "glucose") * 2898),
      "caps at 100 kJ": planted(respiration, (a) => Math.min(n(a, "glucose") * n(a, "energy_per_mole"), 100)),
      "sign flips above 0.003 mol": planted(respiration, (a) => (n(a, "glucose") > 0.003 ? -1 : 1) * n(a, "glucose") * n(a, "energy_per_mole")),
      "NaN at 0.0025 mol": planted(respiration, (a) => (n(a, "glucose") === 0.0025 ? Number.NaN : n(a, "glucose") * n(a, "energy_per_mole"))),
      "square of the glucose": planted(respiration, (a) => n(a, "glucose") * n(a, "glucose") * n(a, "energy_per_mole")),
      "no domain check on the energy per mole": planted(respiration, (a) => n(a, "glucose") * n(a, "energy_per_mole"), ["energy_per_mole"]),
    },
  },
  {
    spec: circular,
    bugs: {
      "forgets the square root": planted(circular, (a) => (G * n(a, "central_mass")) / (n(a, "radius") * 1000) / 1000),
      "multiplies by the radius instead of dividing": planted(circular, (a) => Math.sqrt(G * n(a, "central_mass") * n(a, "radius") * 1000) / 1000),
      "radius left in kilometres": planted(circular, (a) => Math.sqrt((G * n(a, "central_mass")) / n(a, "radius")) / 1000),
      "answer left in metres per second": planted(circular, (a) => Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000))),
      "escape speed used for the circular speed": planted(circular, (a) => Math.sqrt((2 * G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000),
      "radius squared in the denominator": planted(circular, (a) => Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000) ** 2) / 1000),
      "forgets the central mass": planted(circular, (a) => Math.sqrt(G / (n(a, "radius") * 1000)) / 1000),
      "caps at 8 km/s": planted(circular, (a) => Math.min(Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000, 8)),
      "sign flips beyond 40 000 km": planted(circular, (a) => (n(a, "radius") > 40000 ? -1 : 1) * (Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000)),
      "NaN at 6771 km": planted(circular, (a) => (n(a, "radius") === 6771 ? Number.NaN : Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000)),
      "no domain check on the central mass": planted(circular, (a) => Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000, ["central_mass"]),
    },
  },
  {
    spec: escape,
    bugs: {
      "forgets the square root": planted(escape, (a) => (2 * G * n(a, "central_mass")) / (n(a, "radius") * 1000) / 1000),
      "forgets the factor of two": planted(escape, (a) => Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000),
      "factor of two outside the root": planted(escape, (a) => (2 * Math.sqrt((G * n(a, "central_mass")) / (n(a, "radius") * 1000))) / 1000),
      "radius left in kilometres": planted(escape, (a) => Math.sqrt((2 * G * n(a, "central_mass")) / n(a, "radius")) / 1000),
      "answer left in metres per second": planted(escape, (a) => Math.sqrt((2 * G * n(a, "central_mass")) / (n(a, "radius") * 1000))),
      "multiplies by the radius instead of dividing": planted(escape, (a) => Math.sqrt(2 * G * n(a, "central_mass") * n(a, "radius") * 1000) / 1000),
      "forgets the central mass": planted(escape, (a) => Math.sqrt((2 * G) / (n(a, "radius") * 1000)) / 1000),
      "caps at 11 km/s": planted(escape, (a) => Math.min(Math.sqrt((2 * G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000, 11)),
      "NaN at 42 164 km": planted(escape, (a) => (n(a, "radius") === 42164 ? Number.NaN : Math.sqrt((2 * G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000)),
      "no domain check on the radius": planted(escape, (a) => Math.sqrt((2 * G * n(a, "central_mass")) / (n(a, "radius") * 1000)) / 1000, ["radius"]),
    },
  },
  {
    spec: centripetal,
    bugs: {
      "forgets to square the speed": planted(centripetal, (a) => (n(a, "speed") * 1000) / (n(a, "radius") * 1000)),
      "divides by the radius squared": planted(centripetal, (a) => (n(a, "speed") * 1000) ** 2 / (n(a, "radius") * 1000) ** 2),
      "multiplies by the radius": planted(centripetal, (a) => (n(a, "speed") * 1000) ** 2 * (n(a, "radius") * 1000)),
      "speed left in km/s": planted(centripetal, (a) => n(a, "speed") ** 2 / (n(a, "radius") * 1000)),
      "radius left in km": planted(centripetal, (a) => (n(a, "speed") * 1000) ** 2 / n(a, "radius")),
      "answer in km/s2": planted(centripetal, (a) => (n(a, "speed") * 1000) ** 2 / (n(a, "radius") * 1000) / 1000),
      "factor of two": planted(centripetal, (a) => (2 * (n(a, "speed") * 1000) ** 2) / (n(a, "radius") * 1000)),
      "caps at 30": planted(centripetal, (a) => Math.min((n(a, "speed") * 1000) ** 2 / (n(a, "radius") * 1000), 30)),
      "sign flips above 10 km/s": planted(centripetal, (a) => (n(a, "speed") > 10 ? -1 : 1) * ((n(a, "speed") * 1000) ** 2 / (n(a, "radius") * 1000))),
      "NaN at 7.9 km/s": planted(centripetal, (a) => (n(a, "speed") === 7.9 ? Number.NaN : (n(a, "speed") * 1000) ** 2 / (n(a, "radius") * 1000))),
      "no domain check on the radius": planted(centripetal, (a) => (n(a, "speed") * 1000) ** 2 / (n(a, "radius") * 1000), ["radius"]),
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
  {
    spec: wave,
    bugs: {
      "divides frequency by wavelength": planted(wave, (a) => n(a, "frequency") / n(a, "wavelength")),
      "adds instead of multiplying": planted(wave, (a) => n(a, "frequency") + n(a, "wavelength")),
      "period used instead of frequency": planted(wave, (a) => n(a, "wavelength") / n(a, "frequency")),
      "half wavelength": planted(wave, (a) => (n(a, "frequency") * n(a, "wavelength")) / 2),
      "caps at 300 m/s": planted(wave, (a) => Math.min(n(a, "frequency") * n(a, "wavelength"), 300)),
      "ignores wavelength": planted(wave, (a) => n(a, "frequency") * 0.4),
      "squares the frequency": planted(wave, (a) => n(a, "frequency") ** 2 * n(a, "wavelength")),
      "NaN at 50 Hz": planted(wave, (a) => (n(a, "frequency") === 50 ? Number.NaN : n(a, "frequency") * n(a, "wavelength"))),
      "sign flips above 60 Hz": planted(wave, (a) => (n(a, "frequency") > 60 ? -1 : 1) * n(a, "frequency") * n(a, "wavelength")),
      "no domain check on frequency": planted(wave, (a) => n(a, "frequency") * n(a, "wavelength"), ["frequency"]),
      "no domain check on wavelength": planted(wave, (a) => n(a, "frequency") * n(a, "wavelength"), ["wavelength"]),
    },
  },
  {
    spec: newton,
    bugs: {
      "multiplies force by mass": planted(newton, (a) => n(a, "force") * n(a, "mass")),
      "divides mass by force": planted(newton, (a) => n(a, "mass") / Math.max(n(a, "force"), 1e-9)),
      "uses weight (g = 10) instead of force": planted(newton, (a) => (n(a, "force") * 10) / n(a, "mass")),
      "forgets mass": planted(newton, (a) => n(a, "force")),
      "mass squared": planted(newton, (a) => n(a, "force") / n(a, "mass") ** 2),
      "caps at 20 m/s2": planted(newton, (a) => Math.min(n(a, "force") / n(a, "mass"), 20)),
      "NaN with no force": planted(newton, (a) => (n(a, "force") === 0 ? Number.NaN : n(a, "force") / n(a, "mass"))),
      "sign flips above 50 N": planted(newton, (a) => (n(a, "force") > 50 ? -1 : 1) * (n(a, "force") / n(a, "mass"))),
      "rounds to a whole number": planted(newton, (a) => Math.round(n(a, "force") / n(a, "mass"))),
      "no domain check on mass": planted(newton, (a) => n(a, "force") / n(a, "mass"), ["mass"]),
      "no domain check on force": planted(newton, (a) => n(a, "force") / n(a, "mass"), ["force"]),
    },
  },
  {
    spec: cardiac,
    bugs: {
      "forgets the mL to L conversion": planted(cardiac, (a) => n(a, "heart_rate") * n(a, "stroke_volume")),
      "divides by 100": planted(cardiac, (a) => (n(a, "heart_rate") * n(a, "stroke_volume")) / 100),
      "adds instead of multiplying": planted(cardiac, (a) => (n(a, "heart_rate") + n(a, "stroke_volume")) / 1000),
      "ignores stroke volume": planted(cardiac, (a) => (n(a, "heart_rate") * 70) / 1000),
      "ignores heart rate": planted(cardiac, (a) => (72 * n(a, "stroke_volume")) / 1000),
      "caps at 15 L/min": planted(cardiac, (a) => Math.min((n(a, "heart_rate") * n(a, "stroke_volume")) / 1000, 15)),
      "NaN at rest rate 60": planted(cardiac, (a) => (n(a, "heart_rate") === 60 ? Number.NaN : (n(a, "heart_rate") * n(a, "stroke_volume")) / 1000)),
      "per second not per minute": planted(cardiac, (a) => (n(a, "heart_rate") * n(a, "stroke_volume")) / 1000 / 60),
      "rounds to a whole litre": planted(cardiac, (a) => Math.round((n(a, "heart_rate") * n(a, "stroke_volume")) / 1000)),
      "no domain check on heart rate": planted(cardiac, (a) => (n(a, "heart_rate") * n(a, "stroke_volume")) / 1000, ["heart_rate"]),
      "no domain check on stroke volume": planted(cardiac, (a) => (n(a, "heart_rate") * n(a, "stroke_volume")) / 1000, ["stroke_volume"]),
    },
  },
  {
    spec: massChange,
    bugs: {
      "divides by the final mass": planted(massChange, (a) => ((n(a, "final_mass") - n(a, "initial_mass")) / Math.max(n(a, "final_mass"), 1e-9)) * 100),
      "reversed subtraction": planted(massChange, (a) => ((n(a, "initial_mass") - n(a, "final_mass")) / n(a, "initial_mass")) * 100),
      "forgets the times 100": planted(massChange, (a) => (n(a, "final_mass") - n(a, "initial_mass")) / n(a, "initial_mass")),
      "difference only (grams)": planted(massChange, (a) => n(a, "final_mass") - n(a, "initial_mass")),
      "ratio without subtracting one": planted(massChange, (a) => (n(a, "final_mass") / n(a, "initial_mass")) * 100),
      "absolute value hides the loss": planted(massChange, (a) => Math.abs(((n(a, "final_mass") - n(a, "initial_mass")) / n(a, "initial_mass")) * 100)),
      "floors a loss at zero": planted(massChange, (a) => Math.max(((n(a, "final_mass") - n(a, "initial_mass")) / n(a, "initial_mass")) * 100, 0)),
      "caps at 50 per cent": planted(massChange, (a) => Math.min(((n(a, "final_mass") - n(a, "initial_mass")) / n(a, "initial_mass")) * 100, 50)),
      "NaN at no change": planted(massChange, (a) => (n(a, "final_mass") === n(a, "initial_mass") ? Number.NaN : ((n(a, "final_mass") - n(a, "initial_mass")) / n(a, "initial_mass")) * 100)),
      "no domain check on initial mass": planted(massChange, (a) => ((n(a, "final_mass") - n(a, "initial_mass")) / n(a, "initial_mass")) * 100, ["initial_mass"]),
    },
  },
  {
    spec: phSpec,
    bugs: {
      "positive log (pH rises with acidity)": planted(phSpec, (a) => Math.log10(n(a, "h_conc"))),
      "natural log": planted(phSpec, (a) => 0 - Math.log(n(a, "h_conc"))),
      "uses the reciprocal": planted(phSpec, (a) => 1 / n(a, "h_conc")),
      "pOH instead of pH": planted(phSpec, (a) => 14 + Math.log10(n(a, "h_conc"))),
      "log base 2": planted(phSpec, (a) => 0 - Math.log2(n(a, "h_conc"))),
      "rounds to a whole number": planted(phSpec, (a) => Math.round(0 - Math.log10(n(a, "h_conc")))),
      "caps at pH 7": planted(phSpec, (a) => Math.min(0 - Math.log10(n(a, "h_conc")), 7)),
      "floors at pH 1": planted(phSpec, (a) => Math.max(0 - Math.log10(n(a, "h_conc")), 1)),
      "NaN at 0.01": planted(phSpec, (a) => (n(a, "h_conc") === 0.01 ? Number.NaN : 0 - Math.log10(n(a, "h_conc")))),
      "no domain check on concentration": planted(phSpec, (a) => 0 - Math.log10(n(a, "h_conc")), ["h_conc"]),
    },
  },
  {
    spec: gasVol,
    bugs: {
      "divides by molar volume": planted(gasVol, (a) => n(a, "moles") / n(a, "molar_volume")),
      "uses 22.4 always": planted(gasVol, (a) => n(a, "moles") * 22.4),
      "uses 24 always": planted(gasVol, (a) => n(a, "moles") * 24),
      "adds instead of multiplying": planted(gasVol, (a) => n(a, "moles") + n(a, "molar_volume")),
      "cm3 reported as dm3": planted(gasVol, (a) => n(a, "moles") * n(a, "molar_volume") * 1000),
      "caps at 100 dm3": planted(gasVol, (a) => Math.min(n(a, "moles") * n(a, "molar_volume"), 100)),
      "NaN at one mole": planted(gasVol, (a) => (n(a, "moles") === 1 ? Number.NaN : n(a, "moles") * n(a, "molar_volume"))),
      "rounds to a whole dm3": planted(gasVol, (a) => Math.round(n(a, "moles") * n(a, "molar_volume"))),
      "squares the moles": planted(gasVol, (a) => n(a, "moles") ** 2 * n(a, "molar_volume")),
      "no domain check on molar volume": planted(gasVol, (a) => n(a, "moles") * n(a, "molar_volume"), ["molar_volume"]),
    },
  },
  {
    spec: refraction,
    bugs: {
      "degrees fed to the sine as radians": planted(refraction, (a) => (Math.asin(Math.sin(n(a, "incidence_angle")) / n(a, "refractive_index")) * 180) / Math.PI),
      "reports radians, not degrees": planted(refraction, (a) => Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index"))),
      "multiplies by n instead of dividing": planted(refraction, (a) => (Math.asin(Math.min(1, Math.sin((n(a, "incidence_angle") * Math.PI) / 180) * n(a, "refractive_index"))) * 180) / Math.PI),
      "tangent instead of sine": planted(refraction, (a) => (Math.atan(Math.tan((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")) * 180) / Math.PI),
      "returns sin r, not the angle": planted(refraction, (a) => Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")),
      "the ray does not bend": planted(refraction, (a) => n(a, "incidence_angle")),
      "divides by n squared": planted(refraction, (a) => (Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index") ** 2) * 180) / Math.PI),
      "caps at 40 degrees": planted(refraction, (a) => Math.min((Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")) * 180) / Math.PI, 40)),
      "NaN at 45 degrees": planted(refraction, (a) => (n(a, "incidence_angle") === 45 ? Number.NaN : (Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")) * 180) / Math.PI)),
      "rounds to whole degrees": planted(refraction, (a) => Math.round((Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")) * 180) / Math.PI)),
      "no domain check on the angle of incidence": planted(refraction, (a) => (Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")) * 180) / Math.PI, ["incidence_angle"]),
      "no domain check on the refractive index": planted(refraction, (a) => (Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")) * 180) / Math.PI, ["refractive_index"]),
      "accepts 90 degrees and over (no ceiling)": (a) => {
        if (n(a, "refractive_index") < 1 || !(n(a, "incidence_angle") >= 0) || !Number.isFinite(n(a, "incidence_angle")) || !Number.isFinite(n(a, "refractive_index"))) throw new RangeError("outside the domain");
        return (Math.asin(Math.sin((n(a, "incidence_angle") * Math.PI) / 180) / n(a, "refractive_index")) * 180) / Math.PI;
      },
    },
  },
  {
    spec: critical,
    bugs: {
      "sin c = n instead of 1 / n": planted(critical, (a) => (Math.asin(Math.min(1, n(a, "refractive_index"))) * 180) / Math.PI),
      "cosine instead of sine": planted(critical, (a) => (Math.acos(1 / n(a, "refractive_index")) * 180) / Math.PI),
      "reports radians, not degrees": planted(critical, (a) => Math.asin(1 / n(a, "refractive_index"))),
      "tangent instead of sine": planted(critical, (a) => (Math.atan(1 / n(a, "refractive_index")) * 180) / Math.PI),
      "the complement (90 minus c)": planted(critical, (a) => 90 - (Math.asin(1 / n(a, "refractive_index")) * 180) / Math.PI),
      "caps at 80 degrees": planted(critical, (a) => Math.min((Math.asin(1 / n(a, "refractive_index")) * 180) / Math.PI, 80)),
      "NaN at n = 1.5": planted(critical, (a) => (n(a, "refractive_index") === 1.5 ? Number.NaN : (Math.asin(1 / n(a, "refractive_index")) * 180) / Math.PI)),
      "rounds to whole degrees": planted(critical, (a) => Math.round((Math.asin(1 / n(a, "refractive_index")) * 180) / Math.PI)),
      "sign flips above n = 2": planted(critical, (a) => (n(a, "refractive_index") > 2 ? -1 : 1) * ((Math.asin(1 / n(a, "refractive_index")) * 180) / Math.PI)),
      "no domain check on the refractive index": planted(critical, (a) => (Math.asin(1 / n(a, "refractive_index")) * 180) / Math.PI, ["refractive_index"]),
    },
  },
  {
    spec: specificHeat,
    bugs: {
      "adds instead of multiplying": planted(specificHeat, (a) => n(a, "mass") + n(a, "specific_heat") + n(a, "temperature_change")),
      "divides by the mass": planted(specificHeat, (a) => (n(a, "specific_heat") * n(a, "temperature_change")) / n(a, "mass")),
      "forgets the mass": planted(specificHeat, (a) => n(a, "specific_heat") * n(a, "temperature_change")),
      "forgets the temperature change": planted(specificHeat, (a) => n(a, "mass") * n(a, "specific_heat")),
      "per gram (divided by 1000)": planted(specificHeat, (a) => (n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change")) / 1000),
      "squares the temperature change": planted(specificHeat, (a) => n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change") ** 2),
      "caps at 100 kJ": planted(specificHeat, (a) => Math.min(n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change"), 1e5)),
      "NaN at 50 degrees": planted(specificHeat, (a) => (n(a, "temperature_change") === 50 ? Number.NaN : n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change"))),
      "sign flips above 40 degrees": planted(specificHeat, (a) => (n(a, "temperature_change") > 40 ? -1 : 1) * n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change")),
      "rounds to the nearest 1000 J": planted(specificHeat, (a) => Math.round((n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change")) / 1000) * 1000),
      "no domain check on the mass": planted(specificHeat, (a) => n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change"), ["mass"]),
      "no domain check on the specific heat capacity": planted(specificHeat, (a) => n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change"), ["specific_heat"]),
      "no domain check on the temperature change": planted(specificHeat, (a) => n(a, "mass") * n(a, "specific_heat") * n(a, "temperature_change"), ["temperature_change"]),
    },
  },
  {
    spec: transformer,
    bugs: {
      "inverts the turns ratio": planted(transformer, (a) => (n(a, "primary_voltage") * n(a, "primary_turns")) / n(a, "secondary_turns")),
      "adds the turns": planted(transformer, (a) => n(a, "primary_voltage") + n(a, "secondary_turns") - n(a, "primary_turns")),
      "forgets the primary voltage": planted(transformer, (a) => n(a, "secondary_turns") / n(a, "primary_turns")),
      "multiplies by both numbers of turns": planted(transformer, (a) => n(a, "primary_voltage") * n(a, "secondary_turns") * n(a, "primary_turns")),
      "ratio of squares": planted(transformer, (a) => (n(a, "primary_voltage") * n(a, "secondary_turns") ** 2) / n(a, "primary_turns") ** 2),
      "caps at 100 V": planted(transformer, (a) => Math.min((n(a, "primary_voltage") * n(a, "secondary_turns")) / n(a, "primary_turns"), 100)),
      "NaN at 60 secondary turns": planted(transformer, (a) => (n(a, "secondary_turns") === 60 ? Number.NaN : (n(a, "primary_voltage") * n(a, "secondary_turns")) / n(a, "primary_turns"))),
      "sign flips above 500 turns": planted(transformer, (a) => (n(a, "secondary_turns") > 500 ? -1 : 1) * ((n(a, "primary_voltage") * n(a, "secondary_turns")) / n(a, "primary_turns"))),
      "rounds to whole volts": planted(transformer, (a) => Math.round((n(a, "primary_voltage") * n(a, "secondary_turns")) / n(a, "primary_turns"))),
      "no domain check on the primary turns": planted(transformer, (a) => (n(a, "primary_voltage") * n(a, "secondary_turns")) / n(a, "primary_turns"), ["primary_turns"]),
      "no domain check on the secondary turns": planted(transformer, (a) => (n(a, "primary_voltage") * n(a, "secondary_turns")) / n(a, "primary_turns"), ["secondary_turns"]),
      "no domain check on the primary voltage": planted(transformer, (a) => (n(a, "primary_voltage") * n(a, "secondary_turns")) / n(a, "primary_turns"), ["primary_voltage"]),
    },
  },
  {
    spec: halfLife,
    bugs: {
      "loses 10% a half-life": planted(halfLife, (a) => n(a, "initial") * 0.9 ** (n(a, "time") / n(a, "half_life"))),
      "straight-line decay": planted(halfLife, (a) => Math.max(0, n(a, "initial") * (1 - n(a, "time") / (2 * n(a, "half_life"))))),
      "halves only once": planted(halfLife, (a) => (n(a, "time") === 0 ? n(a, "initial") : n(a, "initial") / 2)),
      "time used as the number of half-lives": planted(halfLife, (a) => n(a, "initial") * 0.5 ** n(a, "time")),
      "e to the minus t over T": planted(halfLife, (a) => n(a, "initial") * Math.exp(-n(a, "time") / n(a, "half_life"))),
      "doubles instead of halving": planted(halfLife, (a) => n(a, "initial") * 2 ** (n(a, "time") / n(a, "half_life"))),
      "caps at 300": planted(halfLife, (a) => Math.min(n(a, "initial") * 0.5 ** (n(a, "time") / n(a, "half_life")), 300)),
      "NaN at 20 minutes": planted(halfLife, (a) => (n(a, "time") === 20 ? Number.NaN : n(a, "initial") * 0.5 ** (n(a, "time") / n(a, "half_life")))),
      "sign flips after 30 minutes": planted(halfLife, (a) => (n(a, "time") > 30 ? -1 : 1) * n(a, "initial") * 0.5 ** (n(a, "time") / n(a, "half_life"))),
      "rounds down to whole counts": planted(halfLife, (a) => Math.floor(n(a, "initial") * 0.5 ** (n(a, "time") / n(a, "half_life")))),
      "no domain check on the time": planted(halfLife, (a) => n(a, "initial") * 0.5 ** (n(a, "time") / n(a, "half_life")), ["time"]),
      "no domain check on the half-life": planted(halfLife, (a) => n(a, "initial") * 0.5 ** (n(a, "time") / n(a, "half_life")), ["half_life"]),
      "no domain check on the initial amount": planted(halfLife, (a) => n(a, "initial") * 0.5 ** (n(a, "time") / n(a, "half_life")), ["initial"]),
    },
  },
  {
    spec: relativeAtomicMassSpec,
    bugs: {
      "weights the wrong isotope": planted(relativeAtomicMassSpec, (a) => (n(a, "abundance_1") * n(a, "mass_2") + (100 - n(a, "abundance_1")) * n(a, "mass_1")) / 100),
      "plain average of the two masses": planted(relativeAtomicMassSpec, (a) => (n(a, "mass_1") + n(a, "mass_2")) / 2),
      "forgets to divide by 100": planted(relativeAtomicMassSpec, (a) => n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")),
      "counts only the first isotope": planted(relativeAtomicMassSpec, (a) => (n(a, "abundance_1") * n(a, "mass_1")) / 100),
      "caps at 40": planted(relativeAtomicMassSpec, (a) => Math.min((n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")) / 100, 40)),
      "NaN at 50 percent": planted(relativeAtomicMassSpec, (a) => (n(a, "abundance_1") === 50 ? Number.NaN : (n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")) / 100)),
      "sign flips above 70 percent": planted(relativeAtomicMassSpec, (a) => (n(a, "abundance_1") > 70 ? -1 : 1) * ((n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")) / 100)),
      "rounds to a whole number": planted(relativeAtomicMassSpec, (a) => Math.round((n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")) / 100)),
      "no domain check on the abundance (the ceiling and the floor)": planted(relativeAtomicMassSpec, (a) => (n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")) / 100, ["abundance_1"]),
      "no domain check on the first isotope mass": planted(relativeAtomicMassSpec, (a) => (n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")) / 100, ["mass_1"]),
      "no domain check on the second isotope mass": planted(relativeAtomicMassSpec, (a) => (n(a, "abundance_1") * n(a, "mass_1") + (100 - n(a, "abundance_1")) * n(a, "mass_2")) / 100, ["mass_2"]),
    },
  },
  {
    spec: foodEnergy,
    bugs: {
      "forgets to convert to kilojoules": planted(foodEnergy, (a) => (n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / n(a, "food_mass")),
      "uses 4.18 for water": planted(foodEnergy, (a) => (n(a, "water_mass") * 4.18 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000)),
      "multiplies by the food mass": planted(foodEnergy, (a) => (n(a, "water_mass") * 4.2 * n(a, "temperature_rise") * n(a, "food_mass")) / 1000),
      "divides by the water mass": planted(foodEnergy, (a) => (4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * n(a, "water_mass") * 1000)),
      "caps at 8 kJ/g": planted(foodEnergy, (a) => Math.min((n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000), 8)),
      "NaN at a 40 degree rise": planted(foodEnergy, (a) => (n(a, "temperature_rise") === 40 ? Number.NaN : (n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000))),
      "sign flips above a 40 degree rise": planted(foodEnergy, (a) => (n(a, "temperature_rise") > 40 ? -1 : 1) * ((n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000))),
      "rounds to one decimal": planted(foodEnergy, (a) => Math.round(((n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000)) * 10) / 10),
      "no domain check on the temperature rise": planted(foodEnergy, (a) => (n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000), ["temperature_rise"]),
      "no domain check on the food mass": planted(foodEnergy, (a) => (n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000), ["food_mass"]),
      "no domain check on the water mass": planted(foodEnergy, (a) => (n(a, "water_mass") * 4.2 * n(a, "temperature_rise")) / (n(a, "food_mass") * 1000), ["water_mass"]),
    },
  },
  {
    spec: boyle,
    bugs: {
      "multiplies by the final volume": planted(boyle, (a) => n(a, "initial_pressure") * n(a, "initial_volume") * n(a, "final_volume")),
      "pressure proportional to volume": planted(boyle, (a) => (n(a, "initial_pressure") * n(a, "final_volume")) / n(a, "initial_volume")),
      "adds the volumes": planted(boyle, (a) => n(a, "initial_pressure") + n(a, "initial_volume") - n(a, "final_volume")),
      "ignores the volume change": planted(boyle, (a) => n(a, "initial_pressure")),
      "squares the volume ratio": planted(boyle, (a) => n(a, "initial_pressure") * (n(a, "initial_volume") / n(a, "final_volume")) ** 2),
      "caps at 150 kPa": planted(boyle, (a) => Math.min((n(a, "initial_pressure") * n(a, "initial_volume")) / n(a, "final_volume"), 150)),
      "NaN at 48 cm3": planted(boyle, (a) => (n(a, "final_volume") === 48 ? Number.NaN : (n(a, "initial_pressure") * n(a, "initial_volume")) / n(a, "final_volume"))),
      "sign flips above 60 cm3": planted(boyle, (a) => (n(a, "final_volume") > 60 ? -1 : 1) * ((n(a, "initial_pressure") * n(a, "initial_volume")) / n(a, "final_volume"))),
      "rounds to the nearest 10 kPa": planted(boyle, (a) => Math.round(((n(a, "initial_pressure") * n(a, "initial_volume")) / n(a, "final_volume")) / 10) * 10),
      "no domain check on the final volume": planted(boyle, (a) => (n(a, "initial_pressure") * n(a, "initial_volume")) / n(a, "final_volume"), ["final_volume"]),
      "no domain check on the initial pressure": planted(boyle, (a) => (n(a, "initial_pressure") * n(a, "initial_volume")) / n(a, "final_volume"), ["initial_pressure"]),
      "no domain check on the initial volume": planted(boyle, (a) => (n(a, "initial_pressure") * n(a, "initial_volume")) / n(a, "final_volume"), ["initial_volume"]),
    },
  },
  {
    spec: parallel,
    bugs: {
      "adds the resistances (series)": planted(parallel, (a) => n(a, "resistance_1") + n(a, "resistance_2")),
      "plain average": planted(parallel, (a) => (n(a, "resistance_1") + n(a, "resistance_2")) / 2),
      "multiplies without dividing": planted(parallel, (a) => n(a, "resistance_1") * n(a, "resistance_2")),
      "forgets to invert the sum": planted(parallel, (a) => 1 / n(a, "resistance_1") + 1 / n(a, "resistance_2")),
      "the smaller resistance": planted(parallel, (a) => Math.min(n(a, "resistance_1"), n(a, "resistance_2"))),
      "caps at 2.5 ohm": planted(parallel, (a) => Math.min((n(a, "resistance_1") * n(a, "resistance_2")) / (n(a, "resistance_1") + n(a, "resistance_2")), 2.5)),
      "NaN at 6 ohm": planted(parallel, (a) => (n(a, "resistance_1") === 6 ? Number.NaN : (n(a, "resistance_1") * n(a, "resistance_2")) / (n(a, "resistance_1") + n(a, "resistance_2")))),
      "sign flips above 10 ohm": planted(parallel, (a) => (n(a, "resistance_1") > 10 ? -1 : 1) * ((n(a, "resistance_1") * n(a, "resistance_2")) / (n(a, "resistance_1") + n(a, "resistance_2")))),
      "rounds to a whole ohm": planted(parallel, (a) => Math.round((n(a, "resistance_1") * n(a, "resistance_2")) / (n(a, "resistance_1") + n(a, "resistance_2")))),
      "no domain check on the first resistance": planted(parallel, (a) => (n(a, "resistance_1") * n(a, "resistance_2")) / (n(a, "resistance_1") + n(a, "resistance_2")), ["resistance_1"]),
      "no domain check on the second resistance": planted(parallel, (a) => (n(a, "resistance_1") * n(a, "resistance_2")) / (n(a, "resistance_1") + n(a, "resistance_2")), ["resistance_2"]),
    },
  },
  {
    spec: buoyant,
    bugs: {
      "divides by the density": planted(buoyant, (a) => (n(a, "volume") * n(a, "g")) / n(a, "density")),
      "forgets g": planted(buoyant, (a) => n(a, "volume") * n(a, "density")),
      "forgets the density": planted(buoyant, (a) => n(a, "volume") * n(a, "g")),
      "adds instead of multiplying": planted(buoyant, (a) => n(a, "volume") + n(a, "density") + n(a, "g")),
      "squares the volume": planted(buoyant, (a) => n(a, "volume") ** 2 * n(a, "density") * n(a, "g")),
      "caps at 500 N": planted(buoyant, (a) => Math.min(n(a, "volume") * n(a, "density") * n(a, "g"), 500)),
      "NaN at 0.002 m3": planted(buoyant, (a) => (n(a, "volume") === 0.002 ? Number.NaN : n(a, "volume") * n(a, "density") * n(a, "g"))),
      "sign flips above 0.004 m3": planted(buoyant, (a) => (n(a, "volume") > 0.004 ? -1 : 1) * (n(a, "volume") * n(a, "density") * n(a, "g"))),
      "rounds to a whole newton": planted(buoyant, (a) => Math.round(n(a, "volume") * n(a, "density") * n(a, "g"))),
      "no domain check on the volume": planted(buoyant, (a) => n(a, "volume") * n(a, "density") * n(a, "g"), ["volume"]),
      "no domain check on the density": planted(buoyant, (a) => n(a, "volume") * n(a, "density") * n(a, "g"), ["density"]),
      "no domain check on the g": planted(buoyant, (a) => n(a, "volume") * n(a, "density") * n(a, "g"), ["g"]),
    },
  },
  {
    spec: cellV,
    bugs: {
      "adds the two potentials": planted(cellV, (a) => n(a, "cathode_potential") + n(a, "anode_potential")),
      "anode minus cathode": planted(cellV, (a) => n(a, "anode_potential") - n(a, "cathode_potential")),
      "forgets the anode": planted(cellV, (a) => n(a, "cathode_potential")),
      "absolute difference": planted(cellV, (a) => Math.abs(n(a, "cathode_potential") - n(a, "anode_potential"))),
      "caps at 1 V": planted(cellV, (a) => Math.min(n(a, "cathode_potential") - n(a, "anode_potential"), 1)),
      "NaN at 0.34 V": planted(cellV, (a) => (n(a, "cathode_potential") === 0.34 ? Number.NaN : n(a, "cathode_potential") - n(a, "anode_potential"))),
      "sign flips above 0.5 V": planted(cellV, (a) => (n(a, "cathode_potential") > 0.5 ? -1 : 1) * (n(a, "cathode_potential") - n(a, "anode_potential"))),
      "rounds to one decimal": planted(cellV, (a) => Math.round((n(a, "cathode_potential") - n(a, "anode_potential")) * 10) / 10),
      "no domain check on the cathode potential": planted(cellV, (a) => n(a, "cathode_potential") - n(a, "anode_potential"), ["cathode_potential"]),
      "no domain check on the anode potential": planted(cellV, (a) => n(a, "cathode_potential") - n(a, "anode_potential"), ["anode_potential"]),
    },
  },
  {
    spec: popDensity,
    bugs: {
      "multiplies by the quadrats": planted(popDensity, (a) => (n(a, "total_count") * n(a, "quadrats") * n(a, "quadrat_area"))),
      "forgets the quadrat area": planted(popDensity, (a) => n(a, "total_count") / n(a, "quadrats")),
      "forgets the number of quadrats": planted(popDensity, (a) => n(a, "total_count") / n(a, "quadrat_area")),
      "divides the other way up": planted(popDensity, (a) => (n(a, "quadrats") * n(a, "quadrat_area")) / Math.max(n(a, "total_count"), 1)),
      "adds instead of multiplying": planted(popDensity, (a) => n(a, "total_count") / (n(a, "quadrats") + n(a, "quadrat_area"))),
      "caps at 10": planted(popDensity, (a) => Math.min(n(a, "total_count") / (n(a, "quadrats") * n(a, "quadrat_area")), 10)),
      "NaN at 45 individuals": planted(popDensity, (a) => (n(a, "total_count") === 45 ? Number.NaN : n(a, "total_count") / (n(a, "quadrats") * n(a, "quadrat_area")))),
      "sign flips above 100 individuals": planted(popDensity, (a) => (n(a, "total_count") > 100 ? -1 : 1) * (n(a, "total_count") / (n(a, "quadrats") * n(a, "quadrat_area")))),
      "rounds to a whole number": planted(popDensity, (a) => Math.round(n(a, "total_count") / (n(a, "quadrats") * n(a, "quadrat_area")))),
      "no domain check on the total count": planted(popDensity, (a) => n(a, "total_count") / (n(a, "quadrats") * n(a, "quadrat_area")), ["total_count"]),
      "no domain check on the number of quadrats": planted(popDensity, (a) => n(a, "total_count") / (n(a, "quadrats") * n(a, "quadrat_area")), ["quadrats"]),
      "no domain check on the quadrat area": planted(popDensity, (a) => n(a, "total_count") / (n(a, "quadrats") * n(a, "quadrat_area")), ["quadrat_area"]),
    },
  },
  {
    spec: eEnergy,
    bugs: {
      "forgets the time": planted(eEnergy, (a) => n(a, "voltage") * n(a, "current")),
      "forgets the current": planted(eEnergy, (a) => n(a, "voltage") * n(a, "time")),
      "adds instead of multiplying": planted(eEnergy, (a) => n(a, "voltage") + n(a, "current") + n(a, "time")),
      "divides by the time": planted(eEnergy, (a) => (n(a, "voltage") * n(a, "current")) / Math.max(n(a, "time"), 1)),
      "caps at 1000 J": planted(eEnergy, (a) => Math.min(n(a, "voltage") * n(a, "current") * n(a, "time"), 1000)),
      "NaN at 60 s": planted(eEnergy, (a) => (n(a, "time") === 60 ? Number.NaN : n(a, "voltage") * n(a, "current") * n(a, "time"))),
      "sign flips above 120 s": planted(eEnergy, (a) => (n(a, "time") > 120 ? -1 : 1) * (n(a, "voltage") * n(a, "current") * n(a, "time"))),
      "rounds to the nearest 100 J": planted(eEnergy, (a) => Math.round((n(a, "voltage") * n(a, "current") * n(a, "time")) / 100) * 100),
      "no domain check on the current": planted(eEnergy, (a) => n(a, "voltage") * n(a, "current") * n(a, "time"), ["current"]),
      "no domain check on the time": planted(eEnergy, (a) => n(a, "voltage") * n(a, "current") * n(a, "time"), ["time"]),
      "no domain check on the voltage": planted(eEnergy, (a) => n(a, "voltage") * n(a, "current") * n(a, "time"), ["voltage"]),
    },
  },
  {
    spec: planetG,
    bugs: {
      "radius in km, not metres": planted(planetG, (a) => ((p) => (G * p.mass) / (p.radius * p.radius))(PLANET_DATA[Math.round(n(a, "planet")) - 1]!)),
      "divides by the radius, not its square": planted(planetG, (a) => ((p) => (G * p.mass) / (p.radius * 1000))(PLANET_DATA[Math.round(n(a, "planet")) - 1]!)),
      "Earth's g for every planet": planted(planetG, () => 9.81),
      "the next planet's data": planted(planetG, (a) => ((p) => (G * p.mass) / (p.radius * 1000) ** 2)(PLANET_DATA[Math.min(Math.round(n(a, "planet")), 7)]!)),
      "forgets G": planted(planetG, (a) => ((p) => p.mass / (p.radius * 1000) ** 2)(PLANET_DATA[Math.round(n(a, "planet")) - 1]!)),
      "NaN for Mars": planted(planetG, (a) => (n(a, "planet") === 4 ? Number.NaN : ((p) => (G * p.mass) / (p.radius * 1000) ** 2)(PLANET_DATA[Math.round(n(a, "planet")) - 1]!))),
      "sign flips for the giant planets": planted(planetG, (a) => (n(a, "planet") >= 5 ? -1 : 1) * ((p) => (G * p.mass) / (p.radius * 1000) ** 2)(PLANET_DATA[Math.round(n(a, "planet")) - 1]!)),
      "rounds to a whole number": planted(planetG, (a) => Math.round(((p) => (G * p.mass) / (p.radius * 1000) ** 2)(PLANET_DATA[Math.round(n(a, "planet")) - 1]!))),
      "no domain check on the planet": planted(planetG, (a) => ((p) => (p ? (G * p.mass) / (p.radius * 1000) ** 2 : 0))(PLANET_DATA[Math.round(n(a, "planet")) - 1]), ["planet"]),
    },
  },
  {
    spec: weightSpec,
    bugs: {
      "divides the mass by g": planted(weightSpec, (a) => n(a, "mass") / Math.max(n(a, "gravity"), 1e-9)),
      "adds instead of multiplying": planted(weightSpec, (a) => n(a, "mass") + n(a, "gravity")),
      "forgets the mass": planted(weightSpec, (a) => n(a, "gravity")),
      "uses 10 N/kg everywhere": planted(weightSpec, (a) => n(a, "mass") * 10),
      "caps at 100 N": planted(weightSpec, (a) => Math.min(n(a, "mass") * n(a, "gravity"), 100)),
      "NaN at 2 kg": planted(weightSpec, (a) => (n(a, "mass") === 2 ? Number.NaN : n(a, "mass") * n(a, "gravity"))),
      "sign flips above 50 kg": planted(weightSpec, (a) => (n(a, "mass") > 50 ? -1 : 1) * n(a, "mass") * n(a, "gravity")),
      "rounds to whole newtons": planted(weightSpec, (a) => Math.round(n(a, "mass") * n(a, "gravity"))),
      "no domain check on the mass": planted(weightSpec, (a) => n(a, "mass") * n(a, "gravity"), ["mass"]),
      "no domain check on g": planted(weightSpec, (a) => n(a, "mass") * n(a, "gravity"), ["gravity"]),
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

describe("the registration suite itself", () => {
  const strict = (spec: ScienceSpec, drop: (a: Record<string, number>) => boolean): Impl => {
    const real = guarded(spec);
    return (a) => {
      if (drop(a)) throw new RangeError("refused");
      return real(a);
    };
  };

  it("refuses an implementation that rejects its own inclusive minimum", () => {
    const bug = strict(hookes, (a) => a["load"] === 0);
    expect(registrationFailures(hookes, bug).some((f) => f.includes("should be accepted"))).toBe(true);
  });

  it("refuses an implementation that throws only on doubled inputs (the homogeneity check no longer skips it)", () => {
    const bug = strict(ohm, (a) => (a["voltage"] as number) > 300);
    expect(registrationFailures(ohm, bug).some((f) => f.includes("homogeneous") && f.includes("threw"))).toBe(true);
  });

  it("refuses an implementation that lets infinity through", () => {
    const real = guarded(hookes);
    const bug: Impl = (a) => (a["load"] === Number.POSITIVE_INFINITY ? 1 : real(a));
    expect(registrationFailures(hookes, bug).some((f) => f.includes("Infinity"))).toBe(true);
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


describe("the circular and escape speeds go together", () => {
  it("makes the escape speed the square root of 2 times the circular speed at every radius and mass on the grid", () => {
    for (const radius of circular.grid.radius as number[]) {
      for (const central_mass of circular.grid.central_mass as number[]) {
        const c = circular.fn({ radius, central_mass });
        const e = escape.fn({ radius, central_mass });
        expect(e / c).toBeCloseTo(Math.SQRT2, 12);
      }
    }
  });
  it("makes the centripetal acceleration at the circular speed equal the pull of gravity at that radius", () => {
    const r = 6371;
    const M = 5.972e24;
    const v = circular.fn({ radius: r, central_mass: M });
    const a = centripetal.fn({ speed: v, radius: r });
    const gravity = (G * M) / (r * 1000) ** 2; // G M / r^2
    expect(a / gravity).toBeCloseTo(1, 12);
  });
  it("gives the textbook's two figures for Earth", () => {
    expect(circular.fn({ radius: 6371, central_mass: 5.972e24 })).toBeCloseTo(7.91, 2);
    expect(escape.fn({ radius: 6371, central_mass: 5.972e24 })).toBeCloseTo(11.19, 2);
  });
});
