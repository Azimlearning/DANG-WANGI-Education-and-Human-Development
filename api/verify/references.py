"""Independent Python references for the Kit's science micro-models (layer L3).

Each reference is written by hand from the law, in Python, without reading the TypeScript, and is keyed by the same model id the Kit
records in its provenance. The verifier evaluates these at the control values the browser reports and compares them with what the page
displays. Worked values (arithmetic done by hand, not by running this code):

  mechanics.hookes       F = k x, so x = F / k:      10 N / 50 N/m = 0.2 m;  2 N / 50 N/m = 0.04 m;  4 N / 20 N/m = 0.2 m
  electricity.ohm        V = I R, so I = V / R:      12 V / 4 ohm = 3 A;     6 V / 12 ohm = 0.5 A;   230 V / 46 ohm = 5 A
  fluids.pressure_depth  P = h rho g:                2 m x 1000 x 10 = 20 000 Pa;   10 x 1000 x 9.81 = 98 100 Pa;   0.5 x 13 600 x 10 = 68 000 Pa

Honest limit: the Kit's implementation and these references share an author, so a shared misunderstanding is possible. The textbook
worked examples in P2 are the real independent check (hard constraint 6); until then the citations stay UNVERIFIED.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Reference:
    fn: Callable[..., float]
    inputs: tuple[str, ...]
    params: tuple[str, ...]
    output_unit: str
    input_units: dict[str, str]


def _finite(**values: float) -> None:
    for name, v in values.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise ValueError(f"{name} must be a finite number, got {v!r}")


def hookes(load: float, k: float) -> float:
    """Extension in metres of a spring with constant `k` (N/m) under `load` (N), within the elastic limit."""
    _finite(load=load, k=k)
    if load < 0:
        raise ValueError("load must be 0 N or more")
    if k <= 0:
        raise ValueError("k must be above 0 N/m")
    return load / k


def ohm(voltage: float, resistance: float) -> float:
    """Current in amperes through an ohmic conductor of `resistance` (ohm) across `voltage` (V)."""
    _finite(voltage=voltage, resistance=resistance)
    if voltage < 0:
        raise ValueError("voltage must be 0 V or more")
    if resistance <= 0:
        raise ValueError("resistance must be above 0 ohm")
    return voltage / resistance


def pressure_depth(depth: float, density: float, g: float) -> float:
    """Gauge pressure in pascals at `depth` (m) in a liquid of `density` (kg/m3) with gravitational field strength `g` (m/s2)."""
    _finite(depth=depth, density=density, g=g)
    if depth < 0:
        raise ValueError("depth must be 0 m or more")
    if density <= 0 or g <= 0:
        raise ValueError("density and g must be above 0")
    return depth * density * g


def magnification(image: float, actual: float) -> float:
    """Linear magnification (times) of a specimen of `actual` size (mm) drawn or imaged at `image` size (mm)."""
    _finite(image=image, actual=actual)
    if image < 0:
        raise ValueError("image must be 0 mm or more")
    if actual <= 0:
        raise ValueError("actual must be above 0 mm")
    return image / actual


def sa_to_v_cube(side: float) -> float:
    """Surface area to volume ratio (per cm) of a cube of edge `side` (cm): six faces of side squared over side cubed."""
    _finite(side=side)
    if side <= 0:
        raise ValueError("side must be above 0 cm")
    return (6 * side * side) / (side * side * side)


def photosynthesis_net(light: float, pmax: float, k: float, resp: float) -> float:
    """Net CO2 uptake (mg/h) of a leaf: a saturating gross rate pmax I / (k + I), minus respiration `resp`. A stylised teaching curve."""
    _finite(light=light, pmax=pmax, k=k, resp=resp)
    if light < 0:
        raise ValueError("light must be 0 klux or more")
    if pmax <= 0 or k <= 0:
        raise ValueError("pmax and k must be above 0")
    if resp < 0:
        raise ValueError("resp must be 0 mg/h or more")
    gross = pmax * (light / (k + light))
    return gross - resp


def moles_from_mass(mass: float, molar_mass: float) -> float:
    """Amount of substance (mol) in `mass` grams of a substance of molar mass `molar_mass` (g/mol)."""
    _finite(mass=mass, molar_mass=molar_mass)
    if mass < 0:
        raise ValueError("mass must be 0 g or more")
    if molar_mass <= 0:
        raise ValueError("molar_mass must be above 0 g/mol")
    return mass / molar_mass


def titration_concentration(va: float, vb: float, ma: float, acid_coeff: float, base_coeff: float) -> float:
    """Concentration of the base (mol/dm3) from a A + b B: moles of acid va*ma scaled by b/a, shared among vb of base."""
    _finite(va=va, vb=vb, ma=ma, acid_coeff=acid_coeff, base_coeff=base_coeff)
    if min(va, vb, ma, acid_coeff, base_coeff) <= 0:
        raise ValueError("all of va, vb, ma and the coefficients must be above 0")
    moles_acid = ma * va
    moles_base = moles_acid * base_coeff / acid_coeff
    return moles_base / vb


def dilution(v2: float, m1: float, v1: float) -> float:
    """Concentration (mol/dm3) after taking `v1` of a solution of concentration `m1` and making it up to `v2` (same volume unit)."""
    _finite(v2=v2, m1=m1, v1=v1)
    if min(v2, m1, v1) <= 0:
        raise ValueError("v2, m1 and v1 must be above 0")
    solute = m1 * v1  # the amount of solute does not change
    return solute / v2


def heat_energy(delta_t: float, mass: float, c: float) -> float:
    """Heat (J) absorbed by `mass` grams of solution of specific heat capacity `c` J/(g C) when it warms by `delta_t` C."""
    _finite(delta_t=delta_t, mass=mass, c=c)
    if delta_t < 0:
        raise ValueError("delta_t must be 0 C or more")
    if mass <= 0 or c <= 0:
        raise ValueError("mass and c must be above 0")
    return mass * c * delta_t


def average_rate(volume: float, time: float) -> float:
    """Average rate of reaction (cm3/s): volume of gas collected over the time taken."""
    _finite(volume=volume, time=time)
    if volume < 0:
        raise ValueError("volume must be 0 cm3 or more")
    if time <= 0:
        raise ValueError("time must be above 0 s")
    return volume / time


REFERENCES: dict[str, Reference] = {
    "mechanics.hookes": Reference(hookes, ("load",), ("k",), "m", {"load": "N"}),
    "electricity.ohm": Reference(ohm, ("voltage", "resistance"), (), "A", {"voltage": "V", "resistance": "ohm"}),
    "fluids.pressure_depth": Reference(pressure_depth, ("depth",), ("density", "g"), "Pa", {"depth": "m"}),
    "biology.magnification": Reference(
        magnification, ("image", "actual"), (), "times", {"image": "mm", "actual": "mm"}
    ),
    "biology.sa_to_v_cube": Reference(sa_to_v_cube, ("side",), (), "/cm", {"side": "cm"}),
    "biology.photosynthesis_net": Reference(
        photosynthesis_net, ("light",), ("pmax", "k", "resp"), "mg/h", {"light": "klux"}
    ),
    "chemistry.moles_from_mass": Reference(moles_from_mass, ("mass",), ("molar_mass",), "mol", {"mass": "g"}),
    "chemistry.titration_concentration": Reference(
        titration_concentration, ("va", "vb"), ("ma", "acid_coeff", "base_coeff"), "mol/dm3", {"va": "cm3", "vb": "cm3"}
    ),
    "chemistry.dilution": Reference(dilution, ("v2",), ("m1", "v1"), "mol/dm3", {"v2": "cm3"}),
    "chemistry.heat_energy": Reference(heat_energy, ("delta_t",), ("mass", "c"), "J", {"delta_t": "\u00b0C"}),
    "chemistry.average_rate": Reference(average_rate, ("volume", "time"), (), "cm3/s", {"volume": "cm3", "time": "s"}),
}


def evaluate_model(model_id: str, params: dict[str, float], inputs: dict[str, float]) -> float:
    """The reference value for `model_id`. Raises KeyError for an unknown model and ValueError outside the domain."""
    ref = REFERENCES[model_id]
    if set(inputs) != set(ref.inputs):
        raise ValueError(f"{model_id}: inputs must be exactly {sorted(ref.inputs)}, got {sorted(inputs)}")
    if set(params) != set(ref.params):
        raise ValueError(f"{model_id}: params must be exactly {sorted(ref.params)}, got {sorted(params)}")
    return ref.fn(**inputs, **params)


# Unit factors, written here independently of the Kit's table. A conversion node reports its own factor; L1 checks it against this table so
# a wrong factor in the Kit cannot make a wrong number look right. (Factors are to the SI base unit of the dimension.)
UNIT_SI: dict[str, tuple[str, float]] = {
    "m": ("length", 1.0),
    "cm": ("length", 1e-2),
    "mm": ("length", 1e-3),
    "km": ("length", 1e3),
    "kg": ("mass", 1.0),
    "g": ("mass", 1e-3),
    "s": ("time", 1.0),
    "ms": ("time", 1e-3),
    "min": ("time", 60.0),
    "Pa": ("pressure", 1.0),
    "kPa": ("pressure", 1e3),
    "A": ("current", 1.0),
    "mA": ("current", 1e-3),
    "J": ("energy", 1.0),
    "kJ": ("energy", 1e3),
    "N": ("force", 1.0),
    "V": ("voltage", 1.0),
    "mV": ("voltage", 1e-3),
    "W": ("power", 1.0),
    "cm3": ("volume", 1e-6),
    "dm3": ("volume", 1e-3),
    "mL": ("volume", 1e-6),
    "L": ("volume", 1e-3),
}


def unit_factor(source: str, target: str) -> float:
    """The factor that turns a value in `source` units into `target` units. Raises KeyError for an unknown unit and ValueError across dimensions."""
    a_dim, a = UNIT_SI[source]
    b_dim, b = UNIT_SI[target]
    if a_dim != b_dim:
        raise ValueError(f"{source} ({a_dim}) cannot become {target} ({b_dim})")
    return a / b
