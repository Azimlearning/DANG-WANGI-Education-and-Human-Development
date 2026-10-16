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


REFERENCES: dict[str, Reference] = {
    "mechanics.hookes": Reference(hookes, ("load",), ("k",), "m"),
    "electricity.ohm": Reference(ohm, ("voltage", "resistance"), (), "A"),
    "fluids.pressure_depth": Reference(pressure_depth, ("depth",), ("density", "g"), "Pa"),
}


def evaluate_model(model_id: str, params: dict[str, float], inputs: dict[str, float]) -> float:
    """The reference value for `model_id`. Raises KeyError for an unknown model and ValueError outside the domain."""
    ref = REFERENCES[model_id]
    if set(inputs) != set(ref.inputs):
        raise ValueError(f"{model_id}: inputs must be exactly {sorted(ref.inputs)}, got {sorted(inputs)}")
    if set(params) != set(ref.params):
        raise ValueError(f"{model_id}: params must be exactly {sorted(ref.params)}, got {sorted(params)}")
    return ref.fn(**inputs, **params)
