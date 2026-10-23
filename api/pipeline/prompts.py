"""Layer 5 and the request builders: assemble prompts from packs in cache order, build the kit pack from the manifest, and estimate tokens.

Order of a request: SYSTEM = the core pack, then the role pack's stable part (with the pattern pack and the plan schema, which depend only on the
pattern); USER = the part that varies (kit pack, exemplar, routing, the question, named issues). Two requests that differ only in variables
therefore share a byte-identical system prompt, which a provider can cache. The kit pack is built from the manifest, so it can never name a component
that does not exist.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from api.evidence.registry import CitationBook
from api.kitmanifest import Manifest
from api.llm.types import LLMRequest
from api.models.misconceptions import _tokens
from api.pipeline import failchecks, wording
from api.pipeline.fill import SlotContract
from api.pipeline.plan import Plan, parse
from api.pipeline.plan_checks import PlanIssue, needed_components
from api.prompts import DIR, estimate_tokens, load

MAX_KIT_PACK = 15
REQUEST_TOKEN_CAP = 7000


class RequestTooLarge(ValueError):
    """A request over the token cap. A ValueError, so existing callers and tests that expect one still work; the pipeline catches this one kind."""

BASE_COMPONENTS = ("environment", "slider", "readout", "reset", "bridge")
PATTERN_COMPONENTS = {
    "simulation": ("text", "graph", "convert", "constant"),
    "virtual_experiment": ("text", "graph", "convert", "constant", "table", "stepper", "experiment"),
}


def _signature_line(entry: dict, manifest: Manifest | None = None) -> str:
    line = f"- {entry['signature']}\n  use when: {entry.get('useWhen', '')}\n  needs: {entry['precondition']}"
    model = manifest.models.get(entry["modelId"]) if manifest is not None and entry.get("modelId") else None
    if model is not None:
        # The Plan names a science model by its model id, which the signature above does not contain. Without this line the planner has to guess the id
        # (first real run without an exemplar: PLAN-002 in 3 of 6 attempts) and cannot tell which names are inputs and which are fixed parameters.
        # Short on purpose: the units are already in the `needs:` line, and what inputs and params mean is said once in the planner pack.
        inputs = ", ".join(model.inputs) or "none"
        params = ", ".join(model.params) or "none"
        line += f'\n  in a Plan: "model": "{model.model_id}", inputs: {inputs}, params: {params}'
    return line


def kit_pack_for_plan(plan: Plan, manifest: Manifest) -> list[str]:
    """Exactly the components the Plan names (ids, sorted). The assembler calls only these."""
    names = needed_components(plan) | {
        manifest.models[m.model].export_name for m in plan.models if m.model in manifest.models
    }
    return sorted(n for n in names if manifest.has(n))


def kit_pack_for_question(
    question: str, pattern: str, manifest: Manifest, *, topic: str | None = None, limit: int = MAX_KIT_PACK
) -> list[str]:
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
    # The routed topic is the strongest signal: the models that serve it come first, then the lexical matches.
    served = sorted(m.export_name for m in manifest.models.values() if topic and topic in m.topics)
    models = served + [m for m in models if m not in served]
    return (chosen + models)[:limit]


def render_kit_pack(names: list[str], manifest: Manifest) -> str:
    return "\n".join(_signature_line(manifest.components[n], manifest) for n in names if manifest.has(n))


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
        raise RequestTooLarge(f"the request would be about {total} tokens, over the cap of {REQUEST_TOKEN_CAP}")


def issues_text(issues: list[PlanIssue]) -> str:
    if not issues:
        return ""
    return "Fix these problems from your previous attempt:\n" + "\n".join(
        f"- [{i.code}] {i.path}: {i.message} Hint: {i.hint}" for i in issues
    )


PLANS_DIR = Path(__file__).resolve().parents[2] / "data" / "plans"


def exemplar_for(question: str, topic: str | None, pattern: str) -> Plan | None:
    """The hand-written golden Plan nearest to the question, from the SAME topic only: an exemplar from another topic would invite the
    planner to copy another lesson's science. Prefers the same pattern, then the most shared words. None when the topic has no golden Plan."""
    if not topic:
        return None
    words = set(re.findall(r"[a-z]+", question.lower()))
    best: tuple[int, int, str] | None = None
    chosen: Plan | None = None
    for path in sorted(PLANS_DIR.glob("*.json")):
        try:
            candidate = parse(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if candidate.topic != topic:
            continue
        shared = len(
            {w for w in re.findall(r"[a-z]+", f"{candidate.title} {candidate.goal}".lower()) if len(w) > 3} & words
        )
        key = (int(candidate.pattern == pattern), shared, candidate.id)
        if best is None or key[:2] > best[:2]:
            best, chosen = key, candidate
    return chosen


def plan_request(
    question: str,
    route_summary: str,
    pattern: str,
    manifest: Manifest,
    exemplar: Plan | None = None,
    issues: list[PlanIssue] | None = None,
    topic: str | None = None,
    use_exemplar: bool = True,
) -> LLMRequest:
    """`use_exemplar=False` gives the planner no worked example (an evaluation switch): for a topic with a hand-written golden Plan the exemplar IS the
    answer, so a planner measured with it shows plumbing and cost, not whether a model can plan an Environment on its own."""
    core, planner = load("core"), load("planner")
    schema = (DIR / planner_schema()).read_text(encoding="utf-8")
    example = (exemplar or exemplar_for(question, topic, pattern)) if use_exemplar else None
    stable, variable = planner.render_parts(
        schema=schema.strip(),
        pattern_pack=pattern_pack(pattern),
        kit_pack=render_kit_pack(kit_pack_for_question(question, pattern, manifest, topic=topic), manifest),
        exemplar=example.model_dump_json(indent=None) if example else "(none)",
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


FREE_MAX_TOKENS = 6000
"""Output cap for one whole Free-lane page. The v3 figure of about $0.19 per whole page was measured on a heavier tier; the ledger reserves this cap's cost
before the call is sent."""


def passage_for(book: CitationBook | None, *, ids: tuple[str, ...] | list[str] = (), topic: str | None = None) -> str:
    """What the judge is told the textbook says: the pointer file's one-line `claim`s, which are OUR words. Never the quotation: that is textbook text, it
    lives beside the local corpus only, and sending it to a paid API is not covered by A-8 (rule 13). `ids` first; otherwise every pointer for the topic."""
    if book is None:
        return "(none)"
    chosen = [book.pointers[i] for i in ids if i in book.pointers]
    if not chosen and topic:
        chosen = [p for p in book.pointers.values() if topic in p.topics]
    claims = sorted({p.claim for p in chosen})[:6]
    return "\n".join(f"- {c}" for c in claims) if claims else "(none)"


_FENCE_TAG = re.compile(r"<\s*/?\s*(?:words|script|notes)\b[^>]*>?", re.IGNORECASE)


def fence_safe(text: str) -> str:
    """The judge packs fence what they read in <words>, <script> and <notes>. Text that contains one of those tags could close the fence and write
    instructions outside it, so the tags are removed from anything that goes inside."""
    return _FENCE_TAG.sub("[tag removed]", text)


def wording_request(plan: Plan, passage: str = "(none)") -> LLMRequest:
    """L4 for a Compose Plan: the judge reads the Plan's prose (the page's Kit-owned sentences are these, verbatim) and the textbook claims. The pack's
    stable part is the whole system prompt: the core pack's 'you write plans' role does not apply to a judge."""
    pack = load("verifier_l4")
    stable, variable = pack.render_parts(
        plan_summary=fence_safe(wording.plan_summary(plan)),
        texts=fence_safe(wording.numbered(wording.plan_texts(plan))),
        passage=fence_safe(passage),
    )
    _check(stable, variable)
    return LLMRequest(prompt=variable, purpose="wording", tier="light", system=stable, max_tokens=300)


def free_request(question: str, route_summary: str) -> LLMRequest:
    """The Free lane's whole-page generator. Standard tier: this page is checked less than any other, so it is not written by the cheapest model."""
    pack = load("free")
    stable, variable = pack.render_parts(question=question, route=route_summary)
    _check(stable, variable)
    return LLMRequest(prompt=variable, purpose="free", tier="standard", system=stable, max_tokens=FREE_MAX_TOKENS)


def free_wording_request(topic: str, html: str, passage: str = "(none)") -> LLMRequest:
    """L4 for a Free page: its words and its script (comments removed). For a page no code has checked, this read is the only content check there is.
    The judge is told the ROUTED TOPIC, not the student's question: free text from the student is one more thing that could address the judge. The caller
    refuses a page `wording.unread` says is too big, so what is read here is the whole page."""
    pack = load("verifier_l4_free")
    stable, variable = pack.render_parts(
        topic=fence_safe(topic),
        texts=fence_safe(wording.numbered(wording.page_texts(html))) or "(no text)",
        script=fence_safe(wording.page_script(html)) or "(no script)",
        passage=fence_safe(passage),
    )
    _check(stable, variable)
    return LLMRequest(prompt=variable, purpose="wording_free", tier="standard", system=stable, max_tokens=400)


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
