"""Layer 6: the deterministic assembler. A Plan plus a generation skeleton gives a complete page with no model call.

Skeletons are HTML files with named slots (`/*SLOT:name*/`) in `api/pipeline/skeletons/`. The assembler fills each slot with Kit calls written
from the Plan; it never invents anything the Plan does not say. A Plan the skeleton cannot take is a `gap` (reported, not guessed at). The
only model-written text is a `custom` slot fill, which has already been through the slot contract (fill.py).

Naming: the PRD's Composer places blocks in the UI (hard constraint 5); this is the assembler, a different thing (D-23).
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from api.kitmanifest import Manifest
from api.pipeline.plan import Plan

SKELETONS = Path(__file__).resolve().parent / "skeletons"
_SLOT = re.compile(r"/\*SLOT:(\w+)\*/")
_VAR = re.compile(r"\{\{(\w+)\}\}")

# Which Plan parts each skeleton can take. A part outside the set is a gap.
SKELETON_PARTS: dict[str, frozenset[str]] = {
    "simulation": frozenset(
        {
            "controls",
            "constants",
            "models",
            "readouts",
            "graphs",
            "steps",
            "table",
            "sentences",
            "custom",
            "predict",
            "hints",
            "check",
            "worked",
        }
    ),
    "virtual_experiment": frozenset(
        {
            "experiment",
            "steps",
            "controls",
            "constants",
            "models",
            "readouts",
            "graphs",
            "table",
            "sentences",
            "custom",
            "predict",
            "hints",
            "check",
            "worked",
        }
    ),
}


class AssemblyGap(Exception):
    """The skeleton cannot take this Plan. `part` names what it cannot place."""

    def __init__(self, part: str, reason: str):
        super().__init__(f"{part}: {reason}")
        self.part = part
        self.reason = reason


@dataclass(frozen=True)
class Assembled:
    html: str
    scope: tuple[str, ...]
    """The JavaScript names a custom fill may use (`env` and one variable per control, constant and model)."""
    slots_used: tuple[str, ...] = field(default=())


def js(value: object) -> str:
    """A JSON literal safe inside an inline script: `</` and the line separators cannot end or break it."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def var(kind: str, ident: str) -> str:
    return f"{kind}_{ident}"


def present_parts(plan: Plan) -> set[str]:
    parts = {"controls", "models", "readouts"}
    for name, present in (
        ("constants", plan.constants),
        ("graphs", plan.graphs),
        ("steps", plan.steps),
        ("table", plan.table),
        ("sentences", plan.sentences),
        ("experiment", plan.experiment),
        ("predict", plan.predict),
        ("hints", plan.hints),
        ("check", plan.concept_check),
        ("worked", plan.worked_solution),
        ("custom", plan.custom),
    ):
        if present:
            parts.add(name)
    return parts


def _slots(plan: Plan, manifest: Manifest) -> dict[str, str]:
    def controls_js() -> str:
        return "\n  ".join(
            f"var {var('c', c.id)} = Synapse.slider(env, "
            + js(
                {
                    "id": c.id,
                    "label": c.label,
                    "unit": c.unit,
                    "min": c.min,
                    "max": c.max,
                    "value": c.value,
                    "grid": c.grid,
                }
            )
            + ");"
            for c in plan.controls
        )

    def constants_js() -> str:
        return "\n  ".join(
            f"var {var('k', k.id)} = Synapse.constant({js(k.value)}, " + js({"label": k.label, "unit": k.unit}) + ");"
            for k in plan.constants
        )

    def models_js() -> str:
        lines = []
        for m in plan.models:
            entry = manifest.models[m.model]
            args = [f"{name}: {js(value)}" for name, value in sorted(m.params.items())]
            for name, bound in sorted(m.inputs.items()):
                kind = "c" if any(c.id == bound for c in plan.controls) else "k"
                args.append(f"{name}: {var(kind, bound)}")
            lines.append(f"var {var('m', m.id)} = Synapse.{entry.export_name}({{ {', '.join(args)} }});")
        return "\n  ".join(lines)

    def source_expr(source: str) -> str:
        return var("c", source) if any(c.id == source for c in plan.controls) else var("m", source)

    def readouts_js() -> str:
        lines = []
        for r in plan.readouts:
            entry = manifest.models[next(m.model for m in plan.models if m.id == r.source)]
            value = var("m", r.source)
            if r.convert_to:
                value = f"Synapse.convert({value}, {js(entry.output_unit)}, {js(r.convert_to)})"
            lines.append(
                f"Synapse.readout(env, {{ label: {js(r.label)}, unit: {js(r.unit)}, value: {value}, digits: {r.digits} }});"
            )
        return "\n  ".join(lines)

    def graphs_js() -> str:
        return "\n  ".join(
            f"Synapse.graph(env, {{ title: {js(g.title)}, x: {var('c', g.x)}, y: {var('m', g.source)}, yLabel: {js(g.label)}, yUnit: {js(g.unit)}, digits: {g.digits} }});"
            for g in plan.graphs
        )

    def table_js() -> str:
        if not plan.table:
            return ""
        cols = ",\n    ".join(
            f"{{ label: {js(c.label)}, unit: {js(c.unit)}, value: {source_expr(c.source)}, digits: {c.digits} }}"
            for c in plan.table.columns
        )
        return f"Synapse.table(env, {{ caption: {js(plan.table.caption)}, columns: [\n    {cols}\n  ] }});"

    def experiment_js() -> str:
        e = plan.experiment
        if not e:
            return ""
        return (
            "Synapse.experiment(env, "
            + js(
                {
                    "aim": e.aim,
                    "hypothesis": e.hypothesis,
                    "independent": e.independent,
                    "dependent": e.dependent,
                    "controlled": e.controlled,
                    "apparatus": e.apparatus,
                }
            )
            + ");"
        )

    return {
        "environment": f"var env = Synapse.environment({{ title: {js(plan.title)}, note: {js(plan.note)} }});",
        "controls": controls_js(),
        "constants": constants_js(),
        "models": models_js(),
        "readouts": readouts_js(),
        "graphs": graphs_js(),
        "steps": f"Synapse.stepper(env, {{ steps: {js(list(plan.steps))} }});" if plan.steps else "",
        "table": table_js(),
        "sentences": "\n  ".join(f"Synapse.text(env, {js(s)});" for s in plan.sentences),
        "experiment": experiment_js(),
        "predict": "Synapse.predictCard(env, "
        + js({"prompt": plan.predict.prompt, "choices": plan.predict.choices, "reveal": plan.predict.reveal})
        + ");"
        if plan.predict
        else "",
        "hints": f"Synapse.hintLadder(env, {{ hints: {js(list(plan.hints))} }});" if plan.hints else "",
        "check": "Synapse.conceptCheck(env, "
        + js(
            {
                "question": plan.concept_check.question,
                "options": plan.concept_check.options,
                "correct": plan.concept_check.correct,
                "explanation": plan.concept_check.explanation,
            }
        )
        + ");"
        if plan.concept_check
        else "",
        "worked": f"Synapse.workedSolution(env, {{ steps: {js(list(plan.worked_solution))} }});"
        if plan.worked_solution
        else "",
    }


def scope_names(plan: Plan) -> tuple[str, ...]:
    return (
        "env",
        *(var("c", c.id) for c in plan.controls),
        *(var("k", k.id) for k in plan.constants),
        *(var("m", m.id) for m in plan.models),
    )


def assemble(plan: Plan, manifest: Manifest, fills: dict[str, str] | None = None) -> Assembled:
    """Raises AssemblyGap when the pattern has no skeleton or the skeleton cannot take a part of the Plan."""
    fills = fills or {}
    allowed = SKELETON_PARTS.get(plan.pattern)
    if allowed is None:
        raise AssemblyGap("pattern", f"there is no skeleton for the pattern '{plan.pattern}'")
    for part in sorted(present_parts(plan) - allowed):
        raise AssemblyGap(part, f"the '{plan.pattern}' skeleton has no slot for '{part}'")
    for slot in plan.custom:
        if slot.name not in fills:
            raise AssemblyGap(f"custom:{slot.name}", "no fill was supplied for this custom slot")
    template = (SKELETONS / f"{plan.pattern}.html").read_text(encoding="utf-8")
    slots = _slots(plan, manifest)
    slots["custom"] = "\n  ".join(f"/* custom: {s.name} */\n  {fills[s.name].strip()}" for s in plan.custom)
    used = []

    def fill(m: re.Match[str]) -> str:
        name = m.group(1)
        if name not in slots:
            raise AssemblyGap(name, "the skeleton names a slot the assembler does not know")
        text = slots[name]
        if text:
            used.append(name)
        return text

    body = _SLOT.sub(fill, template)
    body = re.sub(r"\n[ \t]*\n(?=[ \t]*\n)", "\n", body)  # collapse the empty lines left by empty slots
    page = _VAR.sub(lambda m: {"title": html.escape(plan.title), "kit_version": manifest.version}[m.group(1)], body)
    return Assembled(page, scope_names(plan), tuple(used))
