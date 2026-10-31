"""Layer 4: deterministic checks on a Plan, before any HTML exists. Each issue has a stable code (the fail-check registry gives it a layer,
a repair route and the messages), a path into the Plan, a plain message and a one-line hint the planner can act on.

The domain data comes from the built Kit manifest, never from Kit source. The copy-number rule is the SAME function the verifier uses on
the finished page (api/verify/provenance.py), so a sentence the plan checks accept cannot be refused later for an unbacked number.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from pydantic import ValidationError

from api.kitmanifest import Manifest
from api.pipeline import constants as known_constants
from api.pipeline.plan import GraphSpec, Plan
from api.verify.provenance import (
    EARTH_MASSES,
    EARTH_RADIUS_KM,
    ORBIT_ESCAPE_MODEL,
    SCENE_FILL_MIN,
    copy_number_problems,
    orbit_outcome,
)
from api.verify.references import evaluate_model, unit_factor

MAX_GRID_POSITIONS = 40
MAX_MASSES = 8
"""The most masses the Kit's `massHanger` takes (its `MAX_MASSES`)."""
MAX_VALVE_STEPS = 40
"""The most steps the Kit's `valve` takes (its `MAX_VALVE_STEPS`)."""
SCENE_MODELS = {
    "spring": frozenset({"mechanics.hookes"}),
    "titration": frozenset({"chemistry.titration_endpoint_volume"}),
    "fermentation": frozenset({"biology.respiration_energy"}),
    "orbit": frozenset({"physics.circular_speed"}),
    "refraction": frozenset({"physics.refraction_angle"}),
    "pressure": frozenset({"fluids.pressure_depth"}),
}
REFRACTION_FULL = 90.0
"""The refraction scene is drawn to the whole range of an angle of incidence (the Kit's `REFRACTION_FULL`)."""
"""Which science models each scene kind may draw: the scene's picture must be the model's own output."""
MAX_COPY_CHARS = 1800
COPY_FACTOR = {"ms": 1.35}
"""The copy budget of a language relative to English. ASSUMED (D-62): a Malay sentence is about a fifth to a third longer than its English; measured on the drafts."""


MAX_CHAIN_DEPTH = 4
"""How many models deep a chain may run (W18: a model may feed another, as gravity feeds weight and weight feeds a spring)."""


def _value(source: str, at: dict[str, float], controls: dict, constants: dict, instances: dict, depth: int = 0) -> float:
    """The value of a control, a constant or a model instance with the controls at `at` (else at their starting values), from the independent references, following a chain
    of models through their inputs. Raises KeyError or ValueError when it cannot be evaluated."""
    if source in controls:
        return float(at[source]) if source in at else float(controls[source].value)
    if source in constants:
        return float(constants[source].value)
    if depth > MAX_CHAIN_DEPTH:
        raise ValueError("the chain of models is too deep")
    inst = instances[source]
    values = {name: _value(bound, at, controls, constants, instances, depth + 1) for name, bound in inst.inputs.items()}
    return float(evaluate_model(inst.model, dict(inst.params), values))


def _controls_under(source: str, controls: dict, instances: dict, depth: int = 0) -> set[str]:
    """The controls a control or a model instance depends on, through any chain of models."""
    if source in controls:
        return {source}
    inst = instances.get(source)
    if inst is None or depth > MAX_CHAIN_DEPTH:
        return set()
    out: set[str] = set()
    for bound in inst.inputs.values():
        out |= _controls_under(bound, controls, instances, depth + 1)
    return out


def _scene_peak(inst, controls: dict, constants: dict, instances: dict | None = None) -> float | None:  # noqa: ANN001
    """The model instance's output with every control at its maximum, from the independent reference; None where it cannot be evaluated (other checks say why)."""
    pool = {**(instances or {}), inst.id: inst}
    if any(c.surface == "planets" for c in controls.values()):
        # A choice control has no order: the largest output is over every choice, not at the last one (Jupiter pulls harder than Neptune).
        span = _source_range(inst.id, controls, constants, pool)
        return span[1] if span is not None else None
    try:
        return _value(inst.id, {c: controls[c].max for c in controls}, controls, constants, pool)
    except (KeyError, ValueError):
        return None


APPARATUS_FILL_MIN = 0.25
"""A part's fraction channel must reach at least a quarter of its scale somewhere in the controls' range, and never pass it (the verifier's own rule)."""
APPARATUS_LIMITS = {"angle": (0.0, 60.0), "ph": (0.0, 14.0)}
MAX_CORNER_CONTROLS = 6


def _source_range(source: str, controls: dict, constants: dict, instances: dict) -> tuple[float, float] | None:
    """The least and greatest value a control or a model instance takes over every corner of the controls' ranges, from the independent references."""
    if source in controls:
        c = controls[source]
        return (c.min, c.max)
    inst = instances.get(source)
    if inst is None:
        return None
    moving = sorted(_controls_under(source, controls, instances))
    if len(moving) > MAX_CORNER_CONTROLS:
        return None
    # Every corner of the controls' ranges; a choice control (the planets, W18) has no order, so every one of its steps is a corner.
    options = [[controls[b].min + k * (controls[b].max - controls[b].min) / controls[b].grid for k in range(controls[b].grid + 1)] if controls[b].surface == "planets" else [controls[b].min, controls[b].max] for b in moving]
    values: list[float] = []
    for choice in itertools.product(*options):
        try:
            values.append(_value(source, dict(zip(moving, choice, strict=True)), controls, constants, instances))
        except (KeyError, ValueError):
            return None
    return (min(values), max(values)) if values else None


def _apparatus_issues(plan: Plan, manifest: Manifest, add) -> None:  # noqa: ANN001
    """PLAN-022: every part is in the Kit's catalogue, every required channel is bound and no other, each to a control or a model instance, in a unit the channel accepts, at a
    scale that fits the controls' range (a fraction channel) or within its limits (an angle, a pH)."""
    catalogue = manifest.apparatus or {}
    controls = {c.id: c for c in plan.controls}
    constants = {k.id: k for k in plan.constants}
    instances = {m.id: m for m in plan.models}
    for i, part in enumerate(plan.apparatus):
        path = f"apparatus[{i}]"
        info = catalogue.get(part.kind)
        if info is None:
            add("PLAN-022", path, f"The Kit has no apparatus part '{part.kind}'.", f"Use one of the Kit's parts: {sorted(catalogue)}.")
            continue
        channels = info.get("channels", {})
        for name in sorted(set(part.channels) - set(channels)):
            add("PLAN-022", f"{path}.channels.{name}", f"A {part.kind} has no channel '{name}'.", f"Its channels are {sorted(channels)}.")
        for name in sorted(n for n, ch in channels.items() if not ch.get("optional") and n not in part.channels):
            add("PLAN-022", f"{path}.channels", f"A {part.kind} needs its '{name}' channel bound.", f"Bind '{name}' to a control or a model instance.")
        for name, bind in part.channels.items():
            ch = channels.get(name)
            if ch is None:
                continue
            where = f"{path}.channels.{name}"
            if bind.source in constants or (bind.source not in controls and bind.source not in instances):
                add("PLAN-022", where, f"'{bind.source}' is not a control or a model instance, so the {part.kind}'s {name} would show nothing that moves.", "Bind it to a control or a model instance id.")
                continue
            unit = controls[bind.source].unit if bind.source in controls else manifest.models[instances[bind.source].model].output_unit if instances[bind.source].model in manifest.models else None
            accepted = ch.get("units") or []
            if accepted and unit not in accepted:
                add("PLAN-022", where, f"A {part.kind}'s {name} draws a value in {' or '.join(accepted)}, and '{bind.source}' is in {unit}.", f"Bind it to a value in {' or '.join(accepted)}.")
                continue
            span = _source_range(bind.source, controls, constants, instances)
            kind = ch.get("type")
            if kind in APPARATUS_LIMITS:
                if bind.full is not None:
                    add("PLAN-022", where, f"A {part.kind}'s {name} is drawn to its own scale and takes no full.", "Remove full.")
                lo_ok, hi_ok = APPARATUS_LIMITS[kind]
                if span is not None and (span[0] < lo_ok - 1e-9 or span[1] > hi_ok + 1e-9):
                    add("PLAN-022", where, f"'{bind.source}' runs from {span[0]:g} to {span[1]:g}, outside {lo_ok:g} to {hi_ok:g}.", f"Keep it within {lo_ok:g} to {hi_ok:g}.")
                continue
            if bind.full is None:
                add("PLAN-022", where, f"A {part.kind}'s {name} needs a full: the value drawn as full.", "Set full to a little above the largest value it reaches.")
                continue
            if span is None:
                continue
            lo, hi = span
            if lo < -1e-9:
                add("PLAN-022", where, f"'{bind.source}' can be negative ({lo:g}), which a {name} cannot show.", "Bind a channel only to a value that stays at zero or above.")
            elif hi > bind.full * (1 + 1e-9) or hi < bind.full * APPARATUS_FILL_MIN:
                add(
                    "PLAN-022",
                    where,
                    f"The {part.kind}'s {name} is drawn to a full of {bind.full:g} but '{bind.source}' reaches {hi:g}, so it would be {'clipped' if hi > bind.full else 'mostly unused'}.",
                    f"Set full to a value from {hi:g} to {hi / APPARATUS_FILL_MIN:g}.",
                )
        if part.drop is not None:
            _drop_issues(part, path, controls, instances, plan, add)


MAX_DROP_ITEMS = 8


def _drop_issues(part, path: str, controls: dict, instances: dict, plan: Plan, add) -> None:  # noqa: ANN001
    """PLAN-022 for a drop (W17, D-70): its items add up to a plain slider with 2 to 8 steps that starts on a step, used by no other drop, and the part shows what the items do (a
    channel bound to that slider, or to a model the slider feeds), so dropping one onto it visibly changes it."""
    drop = part.drop
    where = f"{path}.drop"
    c = controls.get(drop.source)
    if c is None:
        add("PLAN-022", where, f"A drop adds up to a slider, and '{drop.source}' is not one of the Plan's controls.", "Set source to the id of the slider the items add up to.")
        return
    if c.surface != "slider":
        add("PLAN-022", where, f"The control '{c.id}' is a {c.surface}; a drop needs a plain slider.", "Set its surface to slider.")
        return
    if not 2 <= c.grid <= MAX_DROP_ITEMS:
        add("PLAN-022", where, f"A drop needs a slider with 2 to {MAX_DROP_ITEMS} steps (one per item), and '{c.id}' has {c.grid}.", f"Set its grid to 2 to {MAX_DROP_ITEMS}.")
        return
    at = (c.value - c.min) / ((c.max - c.min) / c.grid)
    if abs(at - round(at)) > 1e-9:
        add("PLAN-022", where, f"'{c.id}' starts at {c.value:g}, between two items.", "Start it on a whole number of items from its minimum.")
    if sum(1 for p in plan.apparatus if p.drop is not None and p.drop.source == c.id) > 1:
        add("PLAN-022", where, f"Two parts take items for '{c.id}'.", "Give each slider at most one drop.")
    fed = {m.id for m in instances.values() if c.id in m.inputs.values()}
    if not any(b.source == c.id or b.source in fed for b in part.channels.values()):
        add("PLAN-022", where, f"Nothing on the {part.kind} changes when an item is dropped onto it.", f"Bind one of its channels to '{c.id}' or to a model it feeds.")


@dataclass(frozen=True)
class PlanIssue:
    code: str
    path: str
    message: str
    hint: str
    repairable: bool = False


def issue_from_validation(exc: ValidationError) -> PlanIssue:
    first = exc.errors()[0]
    where = ".".join(str(p) for p in first["loc"]) or "(plan)"
    return PlanIssue(
        "PLAN-001",
        where,
        f"The plan does not match the schema at {where}: {first['msg']}",
        f"Fix {where}: {first['msg']}",
    )


def needed_components(plan: Plan) -> set[str]:
    need = {"environment", "slider", "readout", "reset", "bridge"}  # the models' own components are added by the caller
    if plan.constants:
        need.add("constant")
    if plan.graphs:
        need.add("graph")
    if plan.table:
        need.add("table")
    if plan.sentences:
        need.add("text")
    if plan.steps:
        need.add("stepper")
    if plan.experiment:
        need.add("experiment")
    if plan.predict:
        need.add("predictCard")
    if plan.hints:
        need.add("hintLadder")
    if plan.concept_check:
        need.add("conceptCheck")
    if plan.worked_solution:
        need.add("workedSolution")
    if any(r.convert_to for r in plan.readouts):
        need.add("convert")
    if any(c.surface == "masses" for c in plan.controls):
        need.add("massHanger")
    if any(c.surface == "valve" for c in plan.controls):
        need.add("valve")
    if any(c.surface == "dial" for c in plan.controls):
        need.add("dial")
    if any(c.surface == "planets" for c in plan.controls):
        need.add("planetPicker")
    if plan.apparatus:
        need.add("apparatus")
    if plan.scene:
        need.add({"titration": "titrationScene", "fermentation": "fermentationScene", "orbit": "orbitScene", "refraction": "refractionScene", "pressure": "pressureScene"}.get(plan.scene.kind, "springScene"))
    return need


def _texts(plan: Plan) -> list[str]:
    out = [plan.title, plan.note, *plan.sentences, *plan.steps, *plan.hints, *plan.worked_solution]
    if plan.predict:
        out += [plan.predict.prompt, *plan.predict.choices, plan.predict.reveal]
    if plan.concept_check:
        out += [plan.concept_check.question, *plan.concept_check.options, plan.concept_check.explanation]
    out += [c.label for c in plan.controls] + [r.label for r in plan.readouts]
    out += [g.title for g in plan.graphs]
    out += [p.label for p in plan.apparatus]
    out += [p.drop.item for p in plan.apparatus if p.drop is not None]
    if plan.table:
        out.append(plan.table.caption)
    if plan.experiment:
        e = plan.experiment
        out += [e.aim, e.hypothesis, e.independent, e.dependent, *e.controlled, *e.apparatus]
    return out


def synthetic_audit(plan: Plan) -> dict:
    """The shape of the Kit's audit for this plan, enough for the verifier's copy-number rule."""
    return {
        "controls": [
            {"id": c.id, "min": c.min, "max": c.max, "default": c.value, "grid": c.grid} for c in plan.controls
        ],
        "constants": [{"label": c.id, "value": c.value} for c in plan.constants],
        "readouts": [
            {"label": m.id, "chain": {"kind": "model", "id": m.model, "params": dict(m.params), "inputs": {}}}
            for m in plan.models
        ],
        "series": [],
        "copy": [{"text": t} for t in _texts(plan)],
    }


# model id: (input that must be at least this parameter, ...). Adding a model with a cross-quantity rule adds a line here.
RELATIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "chemistry.dilution": (("v2", "v1"),),
}

# model id: (input, parameter). The input's control must start at a whole multiple of the parameter and move in whole multiples of it (PLAN-021). The textbook
# states the half-life rule for whole numbers of half-lives only, so a time control that stops between them shows values the book never gives.
WHOLE_MULTIPLES: dict[str, tuple[tuple[str, str], ...]] = {
    "physics.half_life_decay": (("time", "half_life"),),
}



def _over_ceiling(value: float, q) -> bool:  # noqa: ANN001
    """True when `value` is above a quantity's ceiling (a `max`); a quantity with no ceiling never is."""
    if q.max is None or not math.isfinite(value):
        return False
    return value >= q.max if q.max_exclusive else value > q.max


def check(plan: Plan, manifest: Manifest, *, lang: str = "en") -> list[PlanIssue]:
    """`lang` only widens the copy budget: Bahasa Melayu runs longer than English for the same meaning (D-62). Every other rule is about numbers, units and structure."""
    issues: list[PlanIssue] = []
    copy_budget = round(MAX_COPY_CHARS * COPY_FACTOR.get(lang, 1.0))

    def add(code: str, path: str, message: str, hint: str, repairable: bool = False) -> None:
        issues.append(PlanIssue(code, path, message, hint, repairable))

    controls = {c.id: c for c in plan.controls}
    constants = {c.id: c for c in plan.constants}
    instances = {m.id: m for m in plan.models}

    ids = [c.id for c in plan.controls] + [c.id for c in plan.constants] + [m.id for m in plan.models]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        add(
            "PLAN-011",
            dup,
            f"The id '{dup}' is used more than once.",
            f"Give every control, constant and model instance its own id (duplicate: {dup}).",
        )

    for i, c in enumerate(plan.controls):
        path = f"controls[{i}]"
        if not (math.isfinite(c.min) and math.isfinite(c.max) and math.isfinite(c.value)):
            add(
                "PLAN-014", path, f"Control '{c.id}' has a value that is not finite.", f"Use finite numbers for {c.id}."
            )
            continue
        if not c.min < c.max:
            add("PLAN-014", path, f"Control '{c.id}' needs min below max.", f"Set min below max for {c.id}.")
        elif not c.min <= c.value <= c.max:
            add(
                "PLAN-014",
                path,
                f"The starting value of '{c.id}' is outside its range.",
                f"Start {c.id} between {c.min} and {c.max}.",
                repairable=True,
            )

    # PLAN-023 (W18): the planets are a row of eight, so a planets control runs from planet 1 to planet 8 in whole steps, and the planets model is fed only by one.
    for i, c in enumerate(plan.controls):
        if c.surface == "planets" and ((c.min, c.max, c.grid, c.unit) != (1, 8, 7, "planet") or c.value not in (1, 2, 3, 4, 5, 6, 7, 8)):
            add(
                "PLAN-023",
                f"controls[{i}]",
                f"Control '{c.id}' is the planets, so it must run from 1 (Mercury) to 8 (Neptune) with grid 7, unit planet, and start on a whole planet.",
                f"Set '{c.id}' to min 1, max 8, grid 7, unit planet and a whole-number value.",
            )
    planet_controls = {c.id for c in plan.controls if c.surface == "planets"}
    for j, m in enumerate(plan.models):
        if m.model == "physics.planet_gravity" and m.inputs.get("planet") not in planet_controls:
            add(
                "PLAN-023",
                f"models[{j}]",
                f"Model '{m.id}' gives the gravity on a planet, so its input must be a control with surface planets.",
                "Feed planet_gravity from a control with surface planets (min 1, max 8, grid 7, unit planet).",
            )

    for i, c in enumerate(plan.controls):
        if c.surface in ("slider", "planets") or not (math.isfinite(c.min) and math.isfinite(c.max) and math.isfinite(c.value) and c.min < c.max):
            continue
        path = f"controls[{i}]"
        most, what, unit_word = (MAX_MASSES, "masses", "masses") if c.surface == "masses" else (MAX_VALVE_STEPS, f"a {c.surface}", "steps")
        if not 2 <= c.grid <= most:
            add(
                "PLAN-018",
                path,
                f"Control '{c.id}' uses {what}, so grid is the number of {unit_word} and must be from 2 to {most} (it is {c.grid}).",
                f"Set grid for '{c.id}' to the number of {unit_word}, from 2 to {most}, or use a slider.",
            )
            continue
        steps = (c.value - c.min) / ((c.max - c.min) / c.grid)
        # A start outside the range is PLAN-014's to report (and to repair); only a start inside it can be off the steps.
        if c.min <= c.value <= c.max and abs(steps - round(steps)) > 1e-9:
            add(
                "PLAN-018",
                path,
                f"Control '{c.id}' starts at {c.value:g}, which is not a whole number of steps between {c.min:g} and {c.max:g}.",
                f"Start '{c.id}' at {c.min:g} plus a whole number of steps of {(c.max - c.min) / c.grid:g}.",
            )

    if plan.scene is not None:
        scene = plan.scene
        allowed = SCENE_MODELS.get(scene.kind, frozenset())
        if scene.kind == "titration":
            drawn = controls.get(scene.source)
            inst = instances.get(scene.endpoint or "")
            if drawn is None or drawn.unit != "cm3":
                add(
                    "PLAN-019",
                    "scene.source",
                    f"A titration scene draws a control in cm3, and '{scene.source}' is {'not a control' if drawn is None else 'in ' + drawn.unit}.",
                    "Point the scene at the id of the control that is the volume run in, in cm3.",
                )
            elif scene.full < drawn.max or drawn.max / scene.full < SCENE_FILL_MIN:
                add(
                    "PLAN-019",
                    "scene.full",
                    f"The burette's capacity is {scene.full:g} cm3 but the control runs in up to {drawn.max:g} cm3, so the picture would be "
                    f"{'overfull' if scene.full < drawn.max else 'mostly unused'}.",
                    f"Set the scene's full to a value from {drawn.max:g} to {drawn.max / SCENE_FILL_MIN:g}.",
                )
            if inst is None or inst.model not in allowed:
                add(
                    "PLAN-019",
                    "scene.endpoint",
                    f"A titration scene's end point is the output of {sorted(allowed)}, and '{scene.endpoint}' is "
                    f"{'not a model instance in this Plan' if inst is None else 'a ' + inst.model + ' instance'}.",
                    f"Point the scene's endpoint at an instance of {sorted(allowed)}.",
                )
            else:
                if any(bound in controls for bound in inst.inputs.values()):
                    add(
                        "PLAN-019",
                        "scene.endpoint",
                        f"The end point '{inst.id}' follows a control. Where the indicator changes depends on the two solutions, never on how far the student has run.",
                        "Feed the end-point model only constants: the acid's volume and the alkali's concentration.",
                    )
                for other in (m for m in plan.models if m.model == "chemistry.titration_concentration"):
                    if other.inputs.get("va") != inst.inputs.get("va") or any(other.params.get(k) != inst.params.get(k) for k in ("ma", "acid_coeff", "base_coeff")):
                        add(
                            "PLAN-019",
                            "scene.endpoint",
                            f"The end point '{inst.id}' and the concentration '{other.id}' describe different titrations (the acid volume, its concentration or the coefficients differ).",
                            "Give both models the same acid volume, acid concentration and coefficients.",
                        )
                if drawn is not None and drawn.unit == "cm3":
                    at = _scene_peak(inst, controls, constants, instances)
                    if at is not None and not (drawn.min <= at <= drawn.max):
                        add(
                            "PLAN-019",
                            "scene.endpoint",
                            f"The indicator changes at {at:g} cm3, which the control ('{drawn.id}', {drawn.min:g} to {drawn.max:g} cm3) can never reach.",
                            f"Choose the alkali's concentration or the control's range so the end point lies between {drawn.min:g} and {drawn.max:g} cm3.",
                        )
                    elif at is not None and drawn.surface == "valve" and drawn.grid > 0:
                        steps = (at - drawn.min) / ((drawn.max - drawn.min) / drawn.grid)
                        if abs(steps - round(steps)) > 1e-6:
                            add(
                                "PLAN-019",
                                "scene.endpoint",
                                f"The indicator changes at {at:g} cm3, which is not one of the stopcock's steps, so the student could never stop exactly at the end point.",
                                f"Choose the alkali's concentration so the end point sits on a step of '{drawn.id}' (steps of {(drawn.max - drawn.min) / drawn.grid:g} cm3 from {drawn.min:g}).",
                            )
        elif scene.kind == "orbit":
            drawn = controls.get(scene.source)
            circ = instances.get(scene.model or "")
            esc = instances.get(scene.escape or "")
            if drawn is None or drawn.unit != "km/s":
                add(
                    "PLAN-019",
                    "scene.source",
                    f"An orbit scene draws a control in km/s, and '{scene.source}' is {'not a control' if drawn is None else 'in ' + drawn.unit}.",
                    "Point the scene at the id of the control that is the launch speed, in km/s.",
                )
            elif scene.full < drawn.max or drawn.max / scene.full < SCENE_FILL_MIN:
                add(
                    "PLAN-019",
                    "scene.full",
                    f"The scene's scale is {scene.full:g} km/s but the control goes up to {drawn.max:g} km/s, so the launch arrow would be "
                    f"{'overfull' if scene.full < drawn.max else 'mostly unused'}.",
                    f"Set the scene's full to a value from {drawn.max:g} to {drawn.max / SCENE_FILL_MIN:g}.",
                )
            if circ is None or circ.model not in allowed:
                add(
                    "PLAN-019",
                    "scene.model",
                    f"An orbit scene draws the circular speed from {sorted(allowed)}, and '{scene.model}' is "
                    f"{'not a model instance in this Plan' if circ is None else 'a ' + circ.model + ' instance'}.",
                    f"Point the scene's model at an instance of {sorted(allowed)}.",
                )
            if esc is None or esc.model != ORBIT_ESCAPE_MODEL:
                add(
                    "PLAN-019",
                    "scene.escape",
                    f"An orbit scene draws the escape speed from {ORBIT_ESCAPE_MODEL}, and '{scene.escape}' is "
                    f"{'not a model instance in this Plan' if esc is None else 'a ' + esc.model + ' instance'}.",
                    f"Point the scene's escape at an instance of {ORBIT_ESCAPE_MODEL}.",
                )
            if circ is not None and esc is not None and circ.model in allowed and esc.model == ORBIT_ESCAPE_MODEL:
                bound = circ.inputs.get("radius")
                if bound is None or bound != esc.inputs.get("radius") or bound not in constants:
                    add(
                        "PLAN-019",
                        "scene.escape",
                        "The circular and escape speeds must be fed by the same radius, a declared constant.",
                        "Bind both models' radius input to one constant (Earth's radius, in km).",
                    )
                else:
                    r = constants[bound]
                    if r.unit != "km" or not (EARTH_RADIUS_KM[0] <= r.value <= EARTH_RADIUS_KM[1]):
                        add(
                            "PLAN-019",
                            "scene.model",
                            f"The scene is about a cannon on Earth, so the radius must be Earth's, {EARTH_RADIUS_KM[0]:g} to {EARTH_RADIUS_KM[1]:g} km; '{bound}' is {r.value:g} {r.unit}.",
                            "Use Earth's radius, 6371 km, as the radius constant.",
                        )
                mass = circ.params.get("central_mass")
                if mass not in EARTH_MASSES or esc.params.get("central_mass") != mass:
                    add(
                        "PLAN-019",
                        "scene.model",
                        f"The scene is about Earth, so both models need Earth's mass ({' or '.join(f'{m:g}' for m in EARTH_MASSES)} kg); they have {mass} and {esc.params.get('central_mass')}.",
                        "Set central_mass to 5.972e24 on both models.",
                    )
                elif drawn is not None and drawn.unit == "km/s" and bound is not None and bound in constants and constants[bound].unit == "km":
                    try:
                        c_speed = float(evaluate_model(circ.model, dict(circ.params), {"radius": constants[bound].value}))
                        e_speed = float(evaluate_model(esc.model, dict(esc.params), {"radius": constants[bound].value}))
                    except (KeyError, ValueError):
                        c_speed = e_speed = math.nan
                    if math.isfinite(c_speed) and math.isfinite(e_speed) and drawn.grid > 0 and drawn.min < drawn.max:
                        positions = [drawn.min + (drawn.max - drawn.min) * i / drawn.grid for i in range(drawn.grid + 1)]
                        seen = {orbit_outcome(v, c_speed, e_speed) for v in positions}
                        missing = sorted({"falls", "circle", "oval", "escapes"} - seen)
                        if missing:
                            add(
                                "PLAN-019",
                                "scene.source",
                                f"The launch control ({drawn.min:g} to {drawn.max:g} km/s in {drawn.grid} steps) can never show: {', '.join(missing)}. The circular speed is {c_speed:.2f} km/s and the escape speed {e_speed:.2f} km/s.",
                                f"Choose the control's range and steps so some position falls short of {c_speed:.2f} km/s, one is within 2 percent of it, one is between it and {e_speed:.2f} km/s, and one reaches {e_speed:.2f} km/s.",
                            )
        elif scene.kind == "refraction":
            drawn = controls.get(scene.source)
            inst = instances.get(scene.model or "")
            if drawn is None or drawn.unit != "deg":
                add(
                    "PLAN-019",
                    "scene.source",
                    f"A refraction scene draws a control in deg, and '{scene.source}' is {'not a control' if drawn is None else 'in ' + drawn.unit}.",
                    "Point the scene at the id of the control that is the angle of incidence, in deg.",
                )
            elif drawn.min < 0 or drawn.max > REFRACTION_FULL:
                add(
                    "PLAN-019",
                    "scene.source",
                    f"The angle of incidence runs from {drawn.min:g} to {drawn.max:g} degrees; a ray can only meet the boundary at 0 to 90 degrees from the normal.",
                    "Keep the angle of incidence within 0 to 90 degrees.",
                )
            if scene.full != REFRACTION_FULL:
                add(
                    "PLAN-019",
                    "scene.full",
                    f"A refraction scene is drawn to the whole range of an angle, {REFRACTION_FULL:g} degrees; this one says {scene.full:g}.",
                    f"Set the scene's full to {REFRACTION_FULL:g}.",
                )
            if inst is None or inst.model not in allowed:
                add(
                    "PLAN-019",
                    "scene.model",
                    f"A refraction scene draws the angle of refraction from {sorted(allowed)}, and '{scene.model}' is "
                    f"{'not a model instance in this Plan' if inst is None else 'a ' + inst.model + ' instance'}.",
                    f"Point the scene's model at an instance of {sorted(allowed)}.",
                )
            elif inst.inputs.get("incidence_angle") != scene.source:
                add(
                    "PLAN-019",
                    "scene.model",
                    f"The angle of refraction '{inst.id}' is not fed by '{scene.source}', the angle of incidence the scene draws.",
                    f"Bind the refraction model's incidence_angle input to '{scene.source}'.",
                )
        elif scene.kind == "fermentation":
            drawn = controls.get(scene.source)
            inst = instances.get(scene.model or "")
            if drawn is None or drawn.unit != "mol":
                add(
                    "PLAN-019",
                    "scene.source",
                    f"A fermentation scene draws a control in mol, and '{scene.source}' is {'not a control' if drawn is None else 'in ' + drawn.unit}.",
                    "Point the scene at the id of the control that is the glucose fermented, in mol.",
                )
            elif scene.full < drawn.max or drawn.max / scene.full < SCENE_FILL_MIN:
                add(
                    "PLAN-019",
                    "scene.full",
                    f"The scene's scale is {scene.full:g} mol but the control goes up to {drawn.max:g} mol, so the bubbling would be "
                    f"{'overfull' if scene.full < drawn.max else 'mostly unused'}.",
                    f"Set the scene's full to a value from {drawn.max:g} to {drawn.max / SCENE_FILL_MIN:g}.",
                )
            if inst is None or inst.model not in allowed:
                add(
                    "PLAN-019",
                    "scene.model",
                    f"A fermentation scene draws the energy from {sorted(allowed)}, and '{scene.model}' is "
                    f"{'not a model instance in this Plan' if inst is None else 'a ' + inst.model + ' instance'}.",
                    f"Point the scene's model at an instance of {sorted(allowed)}.",
                )
            elif inst.params.get("energy_per_mole") != 210:
                add(
                    "PLAN-019",
                    "scene.model",
                    f"The scene draws alcohol fermentation, which gives 210 kJ per mole of glucose; '{inst.id}' uses {inst.params.get('energy_per_mole')}. The picture (bubbles, cloudy limewater, a warmer tube, ethanol) is false for lactic acid fermentation and for aerobic respiration.",
                    "Point the scene's model at the instance with energy_per_mole 210.",
                )
            elif inst.inputs.get("glucose") != scene.source:
                add(
                    "PLAN-019",
                    "scene.model",
                    f"The energy '{inst.id}' is not fed by '{scene.source}', the control the scene draws.",
                    f"Bind the energy model's glucose input to '{scene.source}'.",
                )
        else:
            inst = instances.get(scene.source)
            if inst is None:
                add(
                    "PLAN-019",
                    "scene.source",
                    f"The scene draws '{scene.source}', which is not a model instance in this Plan.",
                    "Point the scene at the id of a model instance whose output it draws.",
                )
            elif inst.model not in allowed:
                add(
                    "PLAN-019",
                    "scene.source",
                    f"A {scene.kind} scene draws the output of {sorted(allowed)}, not of '{inst.model}'.",
                    f"Draw a {scene.kind} scene only from {sorted(allowed)}, or leave the scene out.",
                )
            else:
                # The drawing scale must fit the model: at the controls' largest values the picture should be nearly full, and never clipped.
                peak = _scene_peak(inst, controls, constants, instances)
                if peak is not None and not (SCENE_FILL_MIN <= peak / scene.full <= 1 + 1e-9):
                    add(
                        "PLAN-019",
                        "scene.full",
                        f"The scene's full scale is {scene.full:g}, but '{inst.id}' reaches {peak:g} at the controls' maximum, so the picture would be "
                        f"{'clipped' if peak > scene.full else 'mostly unused'}.",
                        f"Set the scene's full to a value from {peak:g} to {peak / SCENE_FILL_MIN:g}.",
                    )

    for i, m in enumerate(plan.models):
        path = f"models[{i}]"
        earlier = {x.id: x for x in plan.models[:i]}  # the models that may feed this one (W18): only those listed before it, so a chain has no loop
        entry = manifest.models.get(m.model)
        if entry is None:
            known = ", ".join(sorted(manifest.models)) or "none"
            add(
                "PLAN-002", path, f"The Kit has no science model '{m.model}'.", f"Use one of the Kit's models: {known}."
            )
            continue
        if entry.topics and plan.topic not in entry.topics:
            # S6: a model used under a topic its specification does not list is a model the lesson was not written for.
            add(
                "PLAN-016",
                path,
                f"{m.model} is registered for {', '.join(entry.topics)}, not for the topic '{plan.topic}'.",
                f"Use a model that fits '{plan.topic}', or set topic to one of {', '.join(entry.topics)}.",
            )
        if set(m.params) != set(entry.params):
            add(
                "PLAN-003",
                path,
                f"{m.model} takes parameters {sorted(entry.params)}, not {sorted(m.params)}.",
                f"Give {m.model} exactly the parameters {sorted(entry.params)}.",
            )
        for name, value in m.params.items():
            q = entry.params.get(name)
            if q is None:
                continue
            if not math.isfinite(value) or (value <= q.min if q.exclusive else value < q.min):
                add(
                    "PLAN-003",
                    f"{path}.params.{name}",
                    f"{name} = {value} is outside {m.model}'s domain ({'above' if q.exclusive else 'at least'} {q.min} {q.unit}).",
                    f"Set {name} {'above' if q.exclusive else 'to at least'} {q.min} {q.unit}.",
                )
            elif _over_ceiling(value, q):
                add(
                    "PLAN-003",
                    f"{path}.params.{name}",
                    f"{name} = {value} is outside {m.model}'s domain ({'below' if q.max_exclusive else 'at most'} {q.max} {q.unit}).",
                    f"Set {name} {'below' if q.max_exclusive else 'to at most'} {q.max} {q.unit}.",
                )
        if set(m.inputs) != set(entry.inputs):
            add(
                "PLAN-004",
                path,
                f"{m.model} takes inputs {sorted(entry.inputs)}, not {sorted(m.inputs)}.",
                f"Bind exactly the inputs {sorted(entry.inputs)} of {m.model}.",
            )
        for name, bound in m.inputs.items():
            q = entry.inputs.get(name)
            if q is None:
                continue
            if bound in controls:
                c = controls[bound]
                if c.unit != q.unit:
                    add(
                        "PLAN-004",
                        f"{path}.inputs.{name}",
                        f"Control '{bound}' is in {c.unit} but {m.model} needs {name} in {q.unit}.",
                        f"Use a control in {q.unit} for {name}.",
                    )
                if c.min <= q.min if q.exclusive else c.min < q.min:
                    add(
                        "PLAN-005",
                        f"controls[{list(controls).index(bound)}]",
                        f"Control '{bound}' starts at {c.min}, below {m.model}'s domain for {name} ({'above' if q.exclusive else 'at least'} {q.min} {q.unit}).",
                        f"Make {bound}'s min {'above' if q.exclusive else 'at least'} {q.min}.",
                    )
                if _over_ceiling(c.max, q):
                    add(
                        "PLAN-005",
                        f"controls[{list(controls).index(bound)}]",
                        f"Control '{bound}' can reach {c.max}, above {m.model}'s domain for {name} ({'below' if q.max_exclusive else 'at most'} {q.max} {q.unit}).",
                        f"Make {bound}'s max {'below' if q.max_exclusive else 'at most'} {q.max}.",
                    )
            elif bound in constants:
                k = constants[bound]
                if k.unit != q.unit:
                    add(
                        "PLAN-004",
                        f"{path}.inputs.{name}",
                        f"Constant '{bound}' is in {k.unit} but {m.model} needs {name} in {q.unit}.",
                        f"Use a constant in {q.unit} for {name}.",
                    )
                if k.value <= q.min if q.exclusive else k.value < q.min:
                    add(
                        "PLAN-005",
                        f"constants[{list(constants).index(bound)}]",
                        f"Constant '{bound}' = {k.value} is outside {m.model}'s domain for {name}.",
                        f"Set {bound} {'above' if q.exclusive else 'to at least'} {q.min}.",
                    )
                elif _over_ceiling(k.value, q):
                    add(
                        "PLAN-005",
                        f"constants[{list(constants).index(bound)}]",
                        f"Constant '{bound}' = {k.value} is outside {m.model}'s domain for {name} ({'below' if q.max_exclusive else 'at most'} {q.max} {q.unit}).",
                        f"Set {bound} {'below' if q.max_exclusive else 'to at most'} {q.max}.",
                    )
            elif bound in earlier:
                # W18: a model defined earlier in the Plan may feed this one (gravity feeds weight, weight feeds a spring), in the unit this input needs and inside its domain.
                upstream = manifest.models.get(earlier[bound].model)
                if upstream is not None and upstream.output_unit != q.unit:
                    add(
                        "PLAN-004",
                        f"{path}.inputs.{name}",
                        f"Model '{bound}' gives {upstream.output_unit} but {m.model} needs {name} in {q.unit}.",
                        f"Feed {name} from a model, control or constant in {q.unit}.",
                    )
                span = _source_range(bound, controls, constants, instances)
                if span is not None and (span[0] <= q.min if q.exclusive else span[0] < q.min):
                    add(
                        "PLAN-005",
                        f"{path}.inputs.{name}",
                        f"Model '{bound}' can give {span[0]:g}, below {m.model}'s domain for {name} ({'above' if q.exclusive else 'at least'} {q.min} {q.unit}).",
                        f"Keep the controls feeding '{bound}' where it stays {'above' if q.exclusive else 'at least'} {q.min}.",
                    )
            else:
                add(
                    "PLAN-004",
                    f"{path}.inputs.{name}",
                    f"Input {name} is bound to '{bound}', which is not a control, a constant or a model defined before it.",
                    f"Bind {name} to a control id, a constant id or the id of a model listed earlier.",
                )

        # S5: a relation between an input and a parameter that a per-quantity domain cannot express.
        for input_name, param_name in RELATIONS.get(m.model, ()):
            bound = m.inputs.get(input_name)
            lowest = (
                controls[bound].min if bound in controls else constants[bound].value if bound in constants else None
            )
            floor = m.params.get(param_name)
            if lowest is not None and floor is not None and lowest < floor:
                add(
                    "PLAN-015",
                    path,
                    f"{m.model} needs {input_name} to be at least {param_name} ({floor}), but '{bound}' can be {lowest}.",
                    f"Make '{bound}' start at {floor} or more, or lower {param_name}.",
                )

    # PLAN-021: a control that stands for a number of whole units of a model parameter (half-lives) must start on one and move in whole ones.
    for m in plan.models:
        for input_name, param_name in WHOLE_MULTIPLES.get(m.model, ()):
            bound = m.inputs.get(input_name)
            unit = m.params.get(param_name)
            if bound not in controls or unit is None or not unit > 0:
                continue
            c = controls[bound]
            step = (c.max - c.min) / c.grid if c.grid > 0 else math.nan
            for what, value in (("starts at", c.min), ("moves in steps of", step)):
                ratio = value / unit
                if not math.isfinite(ratio) or abs(ratio - round(ratio)) > 1e-9 or round(ratio) < (0 if what == "starts at" else 1):
                    add(
                        "PLAN-021",
                        f"controls[{list(controls).index(bound)}]",
                        f"Control '{bound}' {what} {value:g}, which is not a whole number of {param_name}s ({unit:g}); the textbook states the rule for whole numbers only.",
                        f"Make '{bound}' start at 0 or a whole multiple of {unit:g} and move in whole multiples of {unit:g} (min, max and grid so that (max - min) / grid is one).",
                    )
                    break

    # PLAN-020: a constant the textbooks fix (g, the molar volume of a gas) must carry a value the textbooks use.
    for i, m in enumerate(plan.models):
        for name, value in m.params.items():
            k = known_constants.find(m.model, name)
            if k is not None and not known_constants.is_accepted(k, value):
                add(
                    "PLAN-020",
                    f"models[{i}].params.{name}",
                    f"{name} = {value:g} {k.unit} is not a value the textbook uses for the {k.name}.",
                    f"Use {known_constants.accepted_text(k)} {k.unit} for the {k.name}.",
                )
    for i, c in enumerate(plan.constants):
        k = known_constants.find(None, None, c.id)
        if k is not None and c.unit == k.unit and not known_constants.is_accepted(k, c.value):
            add(
                "PLAN-020",
                f"constants[{i}]",
                f"{c.id} = {c.value:g} {c.unit} is not a value the textbook uses for the {k.name}.",
                f"Use {known_constants.accepted_text(k)} {k.unit} for the {k.name}.",
            )

    # S4: a control that no readout can show a difference for is a "dead control" to the verifier. Evaluate each readout's model (the independent
    # Python reference) at the control's min and max and compare what the readout would DISPLAY at its digits.
    for ci, c in enumerate(plan.controls):
        if not (math.isfinite(c.min) and math.isfinite(c.max) and c.min < c.max):
            continue
        feeds = [m for m in plan.models if c.id in _controls_under(m.id, controls, instances)]
        shown_any = False
        evaluable = False
        for r in plan.readouts:
            m = instances.get(r.source)
            if m is None or m not in feeds:
                continue
            try:
                texts = [f"{_value(m.id, {c.id: edge}, controls, constants, instances):.{r.digits}f}" for edge in (c.min, c.max)]
            except (KeyError, ValueError):
                continue
            evaluable = True
            shown_any = shown_any or texts[0] != texts[1]
        if feeds and evaluable and not shown_any:
            add(
                "PLAN-017",
                f"controls[{ci}]",
                f"Control '{c.id}' changes no readout's displayed value between {c.min:g} and {c.max:g} at the digits shown.",
                f"Show more digits on a readout that depends on '{c.id}', or widen its range.",
            )

    for i, r in enumerate(plan.readouts):
        path = f"readouts[{i}]"
        inst = instances.get(r.source)
        if inst is None:
            add(
                "PLAN-006",
                path,
                f"Readout '{r.label}' has no source model instance '{r.source}'.",
                f"Point '{r.label}' at one of the plan's model instance ids {sorted(instances)}.",
            )
            continue
        entry = manifest.models.get(inst.model)
        if entry is None:
            continue
        want = r.convert_to or entry.output_unit
        if r.convert_to:
            try:
                unit_factor(entry.output_unit, r.convert_to)
            except (KeyError, ValueError):
                add(
                    "PLAN-007",
                    path,
                    f"{entry.output_unit} cannot be converted to {r.convert_to}.",
                    f"Convert {entry.output_unit} only to a unit of the same kind the Kit knows.",
                )
        if r.unit != want:
            add(
                "PLAN-007",
                path,
                f"Readout '{r.label}' is labelled {r.unit} but shows {want}.",
                f"Label '{r.label}' with {want}.",
            )

    for i, g in enumerate(plan.graphs):
        path = f"graphs[{i}]"
        inst = instances.get(g.source)
        if g.x not in controls:
            add(
                "PLAN-006",
                path,
                f"The graph's x '{g.x}' is not a control.",
                f"Use a control id for x ({sorted(controls)}).",
            )
        if inst is None:
            add(
                "PLAN-006",
                path,
                f"The graph's source '{g.source}' is not a model instance.",
                f"Use a model instance id ({sorted(instances)}).",
            )
        else:
            entry = manifest.models.get(inst.model)
            if entry is not None and g.unit != entry.output_unit:
                add(
                    "PLAN-007",
                    path,
                    f"The graph is labelled {g.unit} but plots {entry.output_unit}.",
                    f"Label the graph {entry.output_unit}.",
                )

    if plan.table:
        for i, col in enumerate(plan.table.columns):
            path = f"table.columns[{i}]"
            if col.source in controls:
                have = controls[col.source].unit
            elif col.source in instances:
                entry = manifest.models.get(instances[col.source].model)
                have = entry.output_unit if entry else col.unit
            else:
                add(
                    "PLAN-006",
                    path,
                    f"Column '{col.label}' has no source '{col.source}'.",
                    "Point each column at a control id or a model instance id.",
                )
                continue
            if col.unit != have:
                add(
                    "PLAN-007",
                    path,
                    f"Column '{col.label}' is labelled {col.unit} but shows {have}.",
                    f"Label '{col.label}' with {have}.",
                )

    if plan.pattern == "virtual_experiment":
        if plan.experiment is None or plan.table is None or not plan.steps:
            add(
                "PLAN-012",
                "pattern",
                "A virtual experiment needs an experiment card, a results table and steps.",
                "Add experiment, table and steps to a virtual_experiment plan.",
            )
    if plan.concept_check and plan.concept_check.correct >= len(plan.concept_check.options):
        add(
            "PLAN-013",
            "concept_check.correct",
            "The correct option number is not one of the options.",
            "Make correct a zero-based index of one of the options.",
        )
    if plan.custom and plan.pattern not in ("simulation", "virtual_experiment"):
        add("PLAN-012", "custom", "Custom slots are not allowed for this pattern.", "Remove the custom slots.")

    _apparatus_issues(plan, manifest, add)

    if sum(len(t) for t in _texts(plan)) > copy_budget:
        add(
            "PLAN-010",
            "(plan)",
            f"The words in the plan add up to more than {copy_budget} characters.",
            "Shorten the note, sentences and steps.",
        )
    if any(c.grid > MAX_GRID_POSITIONS for c in plan.controls):
        add(
            "PLAN-010",
            "controls",
            f"A control has more than {MAX_GRID_POSITIONS} grid intervals.",
            f"Use at most {MAX_GRID_POSITIONS}.",
            repairable=True,
        )

    for component in sorted(
        needed_components(plan)
        | {manifest.models[m.model].export_name for m in plan.models if m.model in manifest.models}
    ):
        if not manifest.has(component):
            add("PLAN-009", "(plan)", f"The Kit has no component '{component}'.", f"Plan without '{component}'.")

    for p in copy_number_problems(synthetic_audit(plan)):
        add(
            "PLAN-008",
            "(copy)",
            p.reason,
            "Remove the number or use a slider value, a declared constant or a model setting.",
        )

    return issues


def draggable(plan: Plan, manifest: Manifest) -> set[str]:
    """The controls a student can operate on the drawing (W20, D-80): a surface (masses, planets, a valve, a dial), a bench channel the catalogue marks as
    grabbable and that is bound to the control itself, or the x of a graph (whose point is a handle, D-78)."""
    out = {c.id for c in plan.controls if c.surface != "slider"}
    catalogue = manifest.apparatus or {}
    for part in plan.apparatus:
        grabs = (catalogue.get(part.kind) or {}).get("grabs") or {}
        out |= {bind.source for name, bind in part.channels.items() if name in grabs}
        if part.drop is not None:
            out.add(part.drop.source)
    out |= {g.x for g in plan.graphs}
    if plan.scene is not None and plan.scene.kind == "orbit":
        out.add(plan.scene.source)  # the launch arrow's tip is a handle (D-78)
    return out & {c.id for c in plan.controls}


def hands_on(plan: Plan, manifest: Manifest) -> Plan:
    """W20 (D-80): the four demos' rule, guaranteed with no model call. A control the student could only move with a slider gets a graph of a readout that depends
    on it, whose point the student drags (D-78). Up to the Plan's two graphs; a readout shown through a unit conversion, or a control whose range does not reach above
    zero (no handle can be drawn for it), is left as it is. The caller checks the Plan again: nothing here is trusted because it was made by code."""
    graphs = list(plan.graphs)
    controls = {c.id: c for c in plan.controls}
    instances = {m.id: m for m in plan.models}
    for c in plan.controls:
        if len(graphs) >= 2:
            break
        if c.id in draggable(plan.model_copy(update={"graphs": graphs}), manifest) or c.max <= 0:
            continue
        readout = next((r for r in plan.readouts if r.convert_to is None and c.id in _controls_under(r.source, controls, instances)), None)
        if readout is None:
            continue
        graphs.append(
            GraphSpec(
                title=f"Drag the point to change the {c.label.lower()}."[:240],  # short: the added words count towards the Plan's 1800-character cap (PLAN-010)
                x=c.id,
                source=readout.source,
                label=readout.label,
                unit=readout.unit,
                digits=readout.digits,
            )
        )
    return plan if len(graphs) == len(plan.graphs) else plan.model_copy(update={"graphs": graphs})


def retopic(plan: Plan, manifest: Manifest, issues: list[PlanIssue]) -> Plan:
    """W19: when the only topic problem is PLAN-016 (the router filed the question under one topic and the planner chose models registered under another),
    and every model in the Plan shares a registered topic, the Plan takes that topic. The topic is routing metadata, not content: a question about particles
    diffusing faster when hot, filed under rate of reaction, is planned with the heat models under heat. Nothing about the lab changes, and every check runs
    again on the result. A second paid plan call for a filing mismatch is avoided."""
    if not any(i.code == "PLAN-016" for i in issues):
        return plan
    shared: set[str] | None = None
    for m in plan.models:
        entry = manifest.models.get(m.model)
        if entry is None or not entry.topics:
            return plan
        shared = set(entry.topics) if shared is None else shared & set(entry.topics)
    if not shared or plan.topic in shared:
        return plan
    return plan.model_copy(update={"topic": sorted(shared)[0]})


def repair(plan: Plan, issues: list[PlanIssue]) -> Plan:
    """Apply the deterministic repairs for the repairable issues: clamp a starting value into its range, cap a grid. Nothing else is guessed."""
    if not any(i.repairable for i in issues):
        return plan
    controls = []
    for c in plan.controls:
        value = min(max(c.value, c.min), c.max) if c.min < c.max else c.value
        controls.append(c.model_copy(update={"value": value, "grid": min(c.grid, MAX_GRID_POSITIONS)}))
    return plan.model_copy(update={"controls": controls})
