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
from api.pipeline.plan import Plan
from api.verify.provenance import copy_number_problems
from api.verify.references import unit_factor

MAX_GRID_POSITIONS = 40
MAX_COPY_CHARS = 1800


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
