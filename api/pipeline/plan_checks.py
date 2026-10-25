"""Layer 4: deterministic checks on a Plan, before any HTML exists. Each issue has a stable code (the fail-check registry gives it a layer,
a repair route and the messages), a path into the Plan, a plain message and a one-line hint the planner can act on.

The domain data comes from the built Kit manifest, never from Kit source. The copy-number rule is the SAME function the verifier uses on
the finished page (api/verify/provenance.py), so a sentence the plan checks accept cannot be refused later for an unbacked number.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pydantic import ValidationError

from api.kitmanifest import Manifest
from api.pipeline import constants as known_constants
from api.pipeline.plan import Plan
from api.verify.provenance import SCENE_FILL_MIN, copy_number_problems
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
}
"""Which science models each scene kind may draw: the scene's picture must be the model's own output."""
MAX_COPY_CHARS = 1800


def _scene_peak(inst, controls: dict, constants: dict) -> float | None:  # noqa: ANN001
    """The model instance's output with every control at its maximum, from the independent reference; None where it cannot be evaluated (other checks say why)."""
    values: dict[str, float] = {}
    for name, bound in inst.inputs.items():
        if bound in controls:
            values[name] = controls[bound].max
        elif bound in constants:
            values[name] = constants[bound].value
        else:
            return None
    try:
        return float(evaluate_model(inst.model, dict(inst.params), values))
    except (KeyError, ValueError):
        return None


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
    if plan.scene:
        need.add({"titration": "titrationScene", "fermentation": "fermentationScene"}.get(plan.scene.kind, "springScene"))
    return need


def _texts(plan: Plan) -> list[str]:
    out = [plan.title, plan.note, *plan.sentences, *plan.steps, *plan.hints, *plan.worked_solution]
    if plan.predict:
        out += [plan.predict.prompt, *plan.predict.choices, plan.predict.reveal]
    if plan.concept_check:
        out += [plan.concept_check.question, *plan.concept_check.options, plan.concept_check.explanation]
    out += [c.label for c in plan.controls] + [r.label for r in plan.readouts]
    out += [g.title for g in plan.graphs]
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


def check(plan: Plan, manifest: Manifest) -> list[PlanIssue]:
    issues: list[PlanIssue] = []

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

    for i, c in enumerate(plan.controls):
        if c.surface == "slider" or not (math.isfinite(c.min) and math.isfinite(c.max) and math.isfinite(c.value) and c.min < c.max):
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
                    at = _scene_peak(inst, controls, constants)
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
                peak = _scene_peak(inst, controls, constants)
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
            else:
                add(
                    "PLAN-004",
                    f"{path}.inputs.{name}",
                    f"Input {name} is bound to '{bound}', which is not a control or a constant.",
                    f"Bind {name} to a control id or a constant id.",
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
        feeds = [m for m in plan.models if c.id in m.inputs.values()]
        shown_any = False
        evaluable = False
        for r in plan.readouts:
            m = instances.get(r.source)
            if m is None or m not in feeds:
                continue
            try:
                texts = []
                for edge in (c.min, c.max):
                    args = {
                        name: (
                            edge
                            if bound == c.id
                            else controls[bound].value
                            if bound in controls
                            else constants[bound].value
                        )
                        for name, bound in m.inputs.items()
                    }
                    texts.append(f"{evaluate_model(m.model, dict(m.params), args):.{r.digits}f}")
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

    if sum(len(t) for t in _texts(plan)) > MAX_COPY_CHARS:
        add(
            "PLAN-010",
            "(plan)",
            f"The words in the plan add up to more than {MAX_COPY_CHARS} characters.",
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


def repair(plan: Plan, issues: list[PlanIssue]) -> Plan:
    """Apply the deterministic repairs for the repairable issues: clamp a starting value into its range, cap a grid. Nothing else is guessed."""
    if not any(i.repairable for i in issues):
        return plan
    controls = []
    for c in plan.controls:
        value = min(max(c.value, c.min), c.max) if c.min < c.max else c.value
        controls.append(c.model_copy(update={"value": value, "grid": min(c.grid, MAX_GRID_POSITIONS)}))
    return plan.model_copy(update={"controls": controls})
