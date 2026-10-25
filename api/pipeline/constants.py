"""Well-known physical and chemical constants, as the KSSM textbooks state them (PLAN-020).

A Plan that sets one of these to a different value is internally consistent and still disagrees with the textbook. The first paid run showed it: the
planner chose g = 10 m/s2 where the book works with 9.81. Nothing else in the plan checks can know that, because a model's domain only says what is
physically possible, not what the book uses.

Each entry is keyed by a model parameter (`model`, `param`) or by a constant id, with its unit, and lists the values the textbooks accept. A value that
is not listed is refused with a hint that names the listed ones. The table is hand-written and small on purpose: a constant that varies by substance
(a specific heat capacity) does not belong here.

ASSUMED (D-47): the accepted values were taken from the Plans the project already checked against the textbook pages (9.81 for g; 22.4 and 24 for the
molar volume of a gas at STP and at room conditions) and from the SI values. A teacher has not reviewed this table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnownConstant:
    name: str
    unit: str
    accepted: tuple[float, ...]
    """Values the textbooks use. A Plan's value must equal one of them."""
    models: tuple[tuple[str, str], ...] = ()
    """(science model id, parameter name) pairs that carry this constant."""
    ids: tuple[str, ...] = ()
    """Constant or control ids a Plan may use for it."""


KNOWN: tuple[KnownConstant, ...] = (
    KnownConstant(
        "gravitational field strength (g)",
        "m/s2",
        (9.81, 9.8),
        models=(("fluids.pressure_depth", "g"),),
        ids=("g", "gravity", "g_field"),
    ),
    KnownConstant(
        "molar volume of a gas",
        "dm3/mol",
        (22.4, 24.0),
        models=(("chemistry.gas_volume", "molar_volume"),),
        ids=("molar_volume", "vm"),
    ),
    KnownConstant("speed of light in a vacuum", "m/s", (3.0e8,), ids=("c_light", "speed_of_light")),
    KnownConstant("Avogadro constant", "1/mol", (6.02e23,), ids=("avogadro", "n_a")),
)


def accepted_text(k: KnownConstant) -> str:
    return " or ".join(f"{v:g}" for v in k.accepted)


def find(model: str | None, param: str | None = None, ident: str | None = None) -> KnownConstant | None:
    for k in KNOWN:
        if model is not None and param is not None and (model, param) in k.models:
            return k
        if ident is not None and ident in k.ids:
            return k
    return None


def is_accepted(k: KnownConstant, value: float) -> bool:
    return any(abs(value - v) <= 1e-9 * max(1.0, abs(v)) for v in k.accepted)
