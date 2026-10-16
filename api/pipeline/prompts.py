"""Layer 5 and the request builders: assemble prompts from packs in cache order, build the kit pack from the manifest, and estimate tokens.

Order of a request: SYSTEM = the core pack, then the role pack's stable part (with the pattern pack and the plan schema, which depend only on the
pattern); USER = the part that varies (kit pack, exemplar, routing, the question, named issues). Two requests that differ only in variables
therefore share a byte-identical system prompt, which a provider can cache. The kit pack is built from the manifest, so it can never name a component
that does not exist.
"""

from __future__ import annotations

import json
import math
from collections import Counter

from api.kitmanifest import Manifest
from api.llm.types import LLMRequest
from api.models.misconceptions import _tokens
from api.pipeline import failchecks
from api.pipeline.fill import SlotContract
from api.pipeline.plan import Plan
from api.pipeline.plan_checks import PlanIssue, needed_components
from api.prompts import DIR, estimate_tokens, load

MAX_KIT_PACK = 15
REQUEST_TOKEN_CAP = 7000
BASE_COMPONENTS = ("environment", "slider", "readout", "reset", "bridge")
PATTERN_COMPONENTS = {
    "simulation": ("text", "graph", "convert", "constant"),
    "virtual_experiment": ("text", "graph", "convert", "constant", "table", "stepper", "experiment"),
}


def _signature_line(entry: dict) -> str:
    return f"- {entry['signature']}\n  use when: {entry.get('useWhen', '')}\n  needs: {entry['precondition']}"


def kit_pack_for_plan(plan: Plan, manifest: Manifest) -> list[str]:
    """Exactly the components the Plan names (ids, sorted). The assembler calls only these."""
    names = needed_components(plan) | {
        manifest.models[m.model].export_name for m in plan.models if m.model in manifest.models
    }
    return sorted(n for n in names if manifest.has(n))


def kit_pack_for_question(question: str, pattern: str, manifest: Manifest, *, limit: int = MAX_KIT_PACK) -> list[str]:
    """The base components for the pattern plus the science models that best match the question (BM25 over each model's useWhen and doc)."""
    chosen = [c for c in (*BASE_COMPONENTS, *PATTERN_COMPONENTS.get(pattern, ())) if manifest.has(c)]
    docs = {
        m.export_name: _tokens(
            " ".join(
                [
                    m.use_when,
                    manifest.components[m.export_name].get("doc", ""),
                    m.model_id.replace(".", " ").replace("_", " "),
                ]
            )
        )
        for m in manifest.models.values()
    }
    df = Counter(t for d in docs.values() for t in set(d))
    q = set(_tokens(question))
    scored = sorted(
        ((sum(math.log(1 + len(docs) / df[t]) for t in q if t in d), name) for name, d in docs.items()),
        key=lambda x: (-x[0], x[1]),
    )
    models = [name for score, name in scored if score > 0] or [name for _, name in scored]
    return (chosen + models)[:limit]


def render_kit_pack(names: list[str], manifest: Manifest) -> str:
    return "\n".join(_signature_line(manifest.components[n]) for n in names if manifest.has(n))


def failure_modes_text(layers: tuple[str, ...] = ("plan", "L1 provenance", "L2 behaviour")) -> str:
    """Generated from the registry, so the packs and the checks cannot disagree. Stable: sorted by code."""
    rank = {layer: i for i, layer in enumerate(layers)}
    ordered = sorted(failchecks.failure_modes(layers), key=lambda f: (rank[f.layer], f.code))
    return "\n".join(f"- {f.code}: {f.model_hint}" for f in ordered[:26])


def pattern_pack(pattern: str) -> str:
    pack = load(f"patterns-{pattern}")
    return pack.render(failure_modes=failure_modes_text()).strip()


def _check(system: str, user: str) -> None:
    total = estimate_tokens(system) + estimate_tokens(user)
    if total > REQUEST_TOKEN_CAP:
        raise ValueError(f"the request would be about {total} tokens, over the cap of {REQUEST_TOKEN_CAP}")


def issues_text(issues: list[PlanIssue]) -> str:
    if not issues:
        return ""
    return "Fix these problems from your previous attempt:\n" + "\n".join(
        f"- [{i.code}] {i.path}: {i.message} Hint: {i.hint}" for i in issues
    )


def plan_request(
    question: str,
    route_summary: str,
    pattern: str,
    manifest: Manifest,
    exemplar: Plan | None = None,
    issues: list[PlanIssue] | None = None,
) -> LLMRequest:
    core, planner = load("core"), load("planner")
    schema = (DIR / planner_schema()).read_text(encoding="utf-8")
    stable, variable = planner.render_parts(
        schema=schema.strip(),
        pattern_pack=pattern_pack(pattern),
        kit_pack=render_kit_pack(kit_pack_for_question(question, pattern, manifest), manifest),
        exemplar=exemplar.model_dump_json(indent=None) if exemplar else "(none)",
        question=question,
        route=route_summary,
        issues=issues_text(issues or []),
    )
    system = core.stable + "\n" + stable
    _check(system, variable)
    return LLMRequest(prompt=variable, purpose="plan", tier="standard", system=system, max_tokens=2000)


def planner_schema() -> str:
    schema = load("planner").schema
    if schema is None:
        raise ValueError("the planner pack declares no schema")
    return schema


def fill_request(
    slot_name: str, purpose: str, contract: SlotContract, scope: tuple[str, ...], issues_msg: str = ""
) -> LLMRequest:
    core, fill = load("core"), load("fill")
    stable, variable = fill.render_parts(
        slot=slot_name,
        purpose=purpose,
        allowed_calls=", ".join(f"Synapse.{c}" for c in sorted(contract.allowed_calls)),
        names=", ".join(scope),
        max_lines=str(contract.max_lines),
        issues=issues_msg,
    )
    system = core.stable + "\n" + stable
    _check(system, variable)
    return LLMRequest(prompt=variable or " ", purpose="fill", tier="light", system=system, max_tokens=400)


def explain_request(question: str, route_summary: str, misconception: str = "(none)") -> LLMRequest:
    core, explain = load("core"), load("explainer")
    stable, variable = explain.render_parts(question=question, route=route_summary, misconception=misconception)
    system = core.stable + "\n" + stable
    _check(system, variable)
    return LLMRequest(prompt=variable or stable, purpose="explain", tier="standard", system=system, max_tokens=600)


def describe(request: LLMRequest) -> dict:
    """A small record of a request for the trace: sizes and a hash, never the question's text."""
    import hashlib

    return {
        "purpose": request.purpose,
        "tier": request.tier,
        "system_tokens": estimate_tokens(request.system or ""),
        "user_tokens": estimate_tokens(request.prompt),
        "system_sha256": hashlib.sha256((request.system or "").encode()).hexdigest()[:16],
    }


def schema_json() -> dict:
    return json.loads((DIR / planner_schema()).read_text(encoding="utf-8"))
