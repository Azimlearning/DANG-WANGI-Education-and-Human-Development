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


def titration_endpoint_volume(va: float, mb: float, ma: float, acid_coeff: float, base_coeff: float) -> float:
    """Volume of base (cm3) that neutralises `va` of acid: the moles of acid va*ma scaled by b/a, divided by the base's concentration `mb`."""
    _finite(va=va, mb=mb, ma=ma, acid_coeff=acid_coeff, base_coeff=base_coeff)
    if min(va, mb, ma, acid_coeff, base_coeff) <= 0:
        raise ValueError("all of va, mb, ma and the coefficients must be above 0")
    moles_base = ma * va * base_coeff / acid_coeff
    return moles_base / mb


# The gravitational constant, N m2/kg2, written here independently of the Kit.
_G = 6.674e-11


def circular_speed(radius: float, central_mass: float) -> float:
    """Speed in km/s of a satellite in a circular orbit `radius` km from the centre of a body of `central_mass` kg: v = sqrt(G M / r)."""
    _finite(radius=radius, central_mass=central_mass)
    if radius <= 0:
        raise ValueError("radius must be above 0 km")
    if central_mass <= 0:
        raise ValueError("central_mass must be above 0 kg")
    return math.sqrt(_G * central_mass / (radius * 1000.0)) / 1000.0


def escape_speed(radius: float, central_mass: float) -> float:
    """Speed in km/s that lets an object leave a body of `central_mass` kg from `radius` km from its centre for good: v = sqrt(2 G M / r)."""
    _finite(radius=radius, central_mass=central_mass)
    if radius <= 0:
        raise ValueError("radius must be above 0 km")
    if central_mass <= 0:
        raise ValueError("central_mass must be above 0 kg")
    return math.sqrt(2.0 * _G * central_mass / (radius * 1000.0)) / 1000.0


def centripetal_acceleration(speed: float, radius: float) -> float:
    """Centripetal acceleration in m/s2 of an object at `speed` (km/s) on a circle of `radius` km: a = v^2 / r."""
    _finite(speed=speed, radius=radius)
    if speed < 0:
        raise ValueError("speed must be 0 km/s or more")
    if radius <= 0:
        raise ValueError("radius must be above 0 km")
    return (speed * 1000.0) ** 2 / (radius * 1000.0)


def respiration_energy(glucose: float, energy_per_mole: float) -> float:
    """Energy (kJ) released when `glucose` mol is broken down by a pathway that gives `energy_per_mole` kJ per mole of glucose."""
    _finite(glucose=glucose, energy_per_mole=energy_per_mole)
    if glucose < 0:
        raise ValueError("glucose must be 0 mol or more")
    if energy_per_mole <= 0:
        raise ValueError("energy_per_mole must be above 0 kJ/mol")
    return glucose * energy_per_mole


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


def wave_speed(frequency: float, wavelength: float) -> float:
    """Speed (m/s) of a wave of `frequency` (Hz) and `wavelength` (m): v = f x lambda."""
    _finite(frequency=frequency, wavelength=wavelength)
    if frequency <= 0 or wavelength <= 0:
        raise ValueError("frequency and wavelength must be above 0")
    return frequency * wavelength


def newton_second(force: float, mass: float) -> float:
    """Acceleration (m/s2) of `mass` (kg) under a resultant `force` (N): a = F / m."""
    _finite(force=force, mass=mass)
    if force < 0:
        raise ValueError("force must be 0 N or more")
    if mass <= 0:
        raise ValueError("mass must be above 0 kg")
    return force / mass


def cardiac_output(heart_rate: float, stroke_volume: float) -> float:
    """Blood pumped per minute (L/min) at `heart_rate` (beats/min) with `stroke_volume` (mL per beat)."""
    _finite(heart_rate=heart_rate, stroke_volume=stroke_volume)
    if heart_rate < 0 or stroke_volume < 0:
        raise ValueError("heart_rate and stroke_volume must be 0 or more")
    millilitres_per_minute = heart_rate * stroke_volume
    return millilitres_per_minute / 1000.0


def percent_change_mass(final_mass: float, initial_mass: float) -> float:
    """Percentage change in mass (%) from `initial_mass` to `final_mass` (both g)."""
    _finite(final_mass=final_mass, initial_mass=initial_mass)
    if final_mass < 0:
        raise ValueError("final_mass must be 0 g or more")
    if initial_mass <= 0:
        raise ValueError("initial_mass must be above 0 g")
    return 100.0 * (final_mass - initial_mass) / initial_mass


def ph_from_h(h_conc: float) -> float:
    """pH of a solution with hydrogen ion concentration `h_conc` (mol/dm3)."""
    _finite(h_conc=h_conc)
    if h_conc <= 0:
        raise ValueError("h_conc must be above 0 mol/dm3")
    return -math.log10(h_conc)


def gas_volume(moles: float, molar_volume: float) -> float:
    """Volume (dm3) of `moles` of gas when one mole occupies `molar_volume` dm3."""
    _finite(moles=moles, molar_volume=molar_volume)
    if moles < 0:
        raise ValueError("moles must be 0 mol or more")
    if molar_volume <= 0:
        raise ValueError("molar_volume must be above 0 dm3/mol")
    return moles * molar_volume


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
    "chemistry.titration_endpoint_volume": Reference(
        titration_endpoint_volume, ("va", "mb"), ("ma", "acid_coeff", "base_coeff"), "cm3", {"va": "cm3", "mb": "mol/dm3"}
    ),
    "physics.circular_speed": Reference(circular_speed, ("radius",), ("central_mass",), "km/s", {"radius": "km"}),
    "physics.centripetal_acceleration": Reference(centripetal_acceleration, ("speed", "radius"), (), "m/s2", {"speed": "km/s", "radius": "km"}),
    "physics.escape_speed": Reference(escape_speed, ("radius",), ("central_mass",), "km/s", {"radius": "km"}),
    "biology.respiration_energy": Reference(respiration_energy, ("glucose",), ("energy_per_mole",), "kJ", {"glucose": "mol"}),
    "chemistry.dilution": Reference(dilution, ("v2",), ("m1", "v1"), "mol/dm3", {"v2": "cm3"}),
    "chemistry.heat_energy": Reference(heat_energy, ("delta_t",), ("mass", "c"), "J", {"delta_t": "\u00b0C"}),
    "chemistry.average_rate": Reference(average_rate, ("volume", "time"), (), "cm3/s", {"volume": "cm3", "time": "s"}),
    "physics.wave_speed": Reference(
        wave_speed, ("frequency", "wavelength"), (), "m/s", {"frequency": "Hz", "wavelength": "m"}
    ),
    "physics.newton_second": Reference(newton_second, ("force", "mass"), (), "m/s2", {"force": "N", "mass": "kg"}),
    "biology.cardiac_output": Reference(
        cardiac_output, ("heart_rate", "stroke_volume"), (), "L/min", {"heart_rate": "beats/min", "stroke_volume": "mL"}
    ),
    "biology.percent_change_mass": Reference(
        percent_change_mass, ("final_mass",), ("initial_mass",), "%", {"final_mass": "g"}
    ),
    "chemistry.ph_from_h": Reference(ph_from_h, ("h_conc",), (), "pH", {"h_conc": "mol/dm3"}),
    "chemistry.gas_volume": Reference(gas_volume, ("moles",), ("molar_volume",), "dm3", {"moles": "mol"}),
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
