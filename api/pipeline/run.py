"""The pipeline orchestrator: the layers of D-23 in order, on whatever LLM service it is given (fakes by default).

    intake -> route -> look up -> explain (text first) -> plan -> plan checks -> assemble -> fill -> verify -> mint, store, gate -> deliver

Every layer writes a trace record. A layer either passes on, repairs deterministically, asks the model once more with named issues, or degrades.
The degrade ladder never leaves a blank screen: Instantiate (a plan assembled with no model-written code), Compose (with checked slot fills), then
the written answer with a plain note. (The labelled Free lane, a whole model-written page, is not built in P3: it needs the paid measurements.)
The text answer streams first, so a failed Environment still leaves a useful answer.

Budgets: at most MAX_LLM_CALLS model calls per request; a request that would exceed it degrades instead of starting another call.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pydantic import ValidationError

from api import kitmanifest
from api.core.errors import SynapseError, envelope_from_exception
from api.evidence.registry import CitationBook
from api.kit import latest_version
from api.llm.service import LLMService
from api.llm.types import LLMRequest
from api.models.misconceptions import default_matcher
from api.pipeline import failchecks, fill, prompts
from api.pipeline import plan as plan_module
from api.pipeline.assemble import Assembled, AssemblyGap, assemble, scope_names
from api.pipeline.grounding import grounding
from api.pipeline.plan import Plan
from api.pipeline.plan_checks import PlanIssue, check, issue_from_validation, repair
from api.routing.router import Route, route
from api.schema.generated import (
    DoneEvent,
    EnvironmentEvent,
    ErrorEnvelope,
    Lane,
    MetaEvent,
    PlanDraft,
    PlanEvent,
    PlanPart,
    StageEvent,
    StreamErrorEvent,
    StreamEvent,
    TextDeltaEvent,
)
from api.sse import split_text
from api.verify.gate import deliver
from api.verify.mint import Evidence, VerificationFailed, VerifiedEnvironment, verify_environment
from api.verify.store import SqliteEnvironmentStore

log = logging.getLogger(__name__)

MAX_LLM_CALLS = 6
MAX_PLAN_ATTEMPTS = 2
MAX_FILL_ATTEMPTS = 2
INJECTION = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above) (?:instructions|rules)|system prompt|<\s*script|developer message|reveal your (?:prompt|instructions)",
    re.IGNORECASE,
)
SUPPORTED_PATTERNS = {
    "simulation": "simulation",
    "virtual_experiment": "virtual_experiment",
    "explorable_diagram": "simulation",
    "data_visualization": "simulation",
}


@dataclass
class TraceRecord:
    layer: str
    status: str
    ms: int
    detail: dict = field(default_factory=dict)


@dataclass
class Trace:
    request_id: str
    question_sha256: str
    records: list[TraceRecord] = field(default_factory=list)
    llm_calls: int = 0
    outcome: str = "unknown"

    def add(self, layer: str, status: str, started: float, **detail: object) -> None:
        self.records.append(TraceRecord(layer, status, int((time.monotonic() - started) * 1000), dict(detail)))

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Deps:
    kit_dist: Path
    public_origin: str
    store: SqliteEnvironmentStore
    llm: LLMService
    trace_path: Path | None = None
    interaction_seconds: float = 10.0
    use_router: bool = True
    evidence: Evidence | None = None
    use_exemplars: bool = True
    """False gives the planner no worked example (evaluation only; see `prompts.plan_request`)."""
    citations: CitationBook | None = None
    """Resolves a Plan's citation ids to corpus-proved citations. Used only together with `evidence` (the same corpus), or nothing is grounded."""
    verify_fn: Callable[..., VerifiedEnvironment] | None = None
    """Test seam: replaces verify_environment (it must have the same keyword arguments)."""


class BudgetExceeded(Exception):
    pass


class _Run:
    def __init__(self, question: str, deps: Deps):
        self.q = " ".join(question.split())
        self.deps = deps
        self.request_id = uuid.uuid4().hex
        self.trace = Trace(self.request_id, hashlib.sha256(self.q.encode()).hexdigest()[:16])
        self.version = latest_version(deps.kit_dist)
        self.manifest = kitmanifest.load(deps.kit_dist, self.version)

    async def complete(self, request: LLMRequest):  # noqa: ANN201
        """The only way any layer reaches the model: it counts against the request's budget and writes a trace record."""
        if self.trace.llm_calls >= MAX_LLM_CALLS:
            raise BudgetExceeded(request.purpose)
        self.trace.llm_calls += 1
        started = time.monotonic()
        result = await self.deps.llm.complete(request)
        self.trace.add(
            f"llm:{request.purpose}",
            "ok",
            started,
            **prompts.describe(request),
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
        )
        return result

    async def call(self, request: LLMRequest, layer: str) -> str:  # noqa: ARG002
        return (await self.complete(request)).text


def canonical_question(question: str) -> str:
    """Lowercase words only, single spaces: 'Why does a spring stretch?' and 'why does a SPRING stretch' are the same question."""
    return " ".join(re.findall(r"[a-z0-9]+", question.lower()))


def _stage(layer: str, status: str, note: str | None = None) -> StageEvent:
    return StageEvent(type="stage", layer=layer, status=status, note=note)  # type: ignore[arg-type]


def draft_of(plan: Plan) -> PlanDraft:
    return PlanDraft(
        title=plan.title,
        goal=plan.goal,
        pattern=plan.pattern,
        note=plan.note,
        controls=[PlanPart(label=c.label, unit=c.unit) for c in plan.controls],
        readouts=[PlanPart(label=r.label, unit=r.unit) for r in plan.readouts],
        hasGraph=bool(plan.graphs),
        hasTable=plan.table is not None,
        steps=list(plan.steps),
    )


def _route_summary(r: Route) -> str:
    return f"topic={r.topic.value}; domain={r.domain.value}; pattern={r.pattern.value}; complexity={r.complexity.value}"


async def run(question: str, deps: Deps) -> AsyncIterator[StreamEvent]:
    """Yield the wire events for one question. Never raises for a model or verification problem; those degrade."""
    try:
        r = _Run(question, deps)
    except FileNotFoundError:
        # No Kit is built (an operator mistake). The stream still ends properly: one named error and `done`, never a broken connection.
        log.error("no Kit is built in %s", deps.kit_dist)
        yield StreamErrorEvent(
            type="error",
            error=ErrorEnvelope(
                code="internal",
                message="This server has no interactive library built, so it cannot make Environments. Ask the operator to build the Kit.",
                issues=[],
                retryable=False,
            ),
        )
        yield DoneEvent(type="done")
        return
    yield MetaEvent(type="meta", requestId=r.request_id, kitVersion=r.version)
    try:
        async for event in _layers(r):
            yield event
    except SynapseError as exc:
        yield StreamErrorEvent(type="error", error=envelope_from_exception(exc))
        r.trace.outcome = "error"
    except Exception as exc:  # noqa: BLE001 - a bug must not leave the stream hanging
        log.exception("pipeline failure")
        yield StreamErrorEvent(type="error", error=envelope_from_exception(exc))
        r.trace.outcome = "error"
    finally:
        _write_trace(r)
    yield DoneEvent(type="done")


def _write_trace(r: _Run) -> None:
    if r.deps.trace_path is None:
        return
    r.deps.trace_path.parent.mkdir(parents=True, exist_ok=True)
    with r.deps.trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(r.trace.as_dict(), sort_keys=True) + "\n")


async def _layers(r: _Run) -> AsyncIterator[StreamEvent]:
    t = r.trace
    # 0 intake
    started = time.monotonic()
    yield _stage("intake", "start")
    if INJECTION.search(r.q):
        t.add("intake", "refused", started, reason="injection_pattern")
        t.outcome = "refused"
        reg = failchecks.get("INTAKE")
        yield _stage(
            "intake",
            "degraded",
            "That question cannot be answered here. Try asking a science question from your textbook.",
        )
        yield TextDeltaEvent(type="text_delta", text=reg.student_message)
        return
    t.add("intake", "ok", started)
    yield _stage("intake", "done")

    # 1 route
    started = time.monotonic()
    yield _stage("route", "start")
    decision = await route(r.q, llm=r if r.deps.use_router else None)  # type: ignore[arg-type]  # _Run exposes the LLMService.complete shape
    t.add(
        "route", "ok", started, **{h: {"value": d.value, "source": d.source} for h, d in decision.decisions().items()}
    )
    route_text = _route_summary(decision)
    yield _stage("route", "done")

    # 2 look up (misconceptions now; the library and the textbook arrive in P5 and P2)
    started = time.monotonic()
    hits = default_matcher().match(r.q, top=1)
    misconception = hits[0].statement if hits else "(none)"
    t.add("lookup", "ok", started, misconception=hits[0].id if hits else None)

    # 3 the written answer always goes first
    started = time.monotonic()
    yield _stage("explain", "start")
    try:
        answer = await r.call(prompts.explain_request(r.q, route_text, misconception), "explain")
    except BudgetExceeded:
        answer = failchecks.get("BUDGET").student_message
    for chunk in split_text(answer):
        yield TextDeltaEvent(type="text_delta", text=chunk)
    t.add("explain", "ok", started)
    yield _stage("explain", "done")

    # 2b library hit: the same canonical question gets the same verified Environment back with no planning, no verification run and no further model
    # call. The gate re-checks it exactly as for a fresh one (a stale, tampered or withdrawn Environment is not served), and a refusal falls through to
    # generating a new one.
    canon = canonical_question(r.q)
    cached_id = r.deps.store.lookup_question(canon)
    if cached_id is not None:
        started = time.monotonic()
        try:
            block = deliver(
                r.deps.store,
                cached_id,
                public_origin=r.deps.public_origin,
                kit_dist=r.deps.kit_dist,
                evidence=r.deps.evidence,
            )
        except VerificationFailed as failure:
            t.add("library", "refused", started, rule=failure.rule)
        else:
            t.add("library", "hit", started, env_id=cached_id[:12])
            t.outcome = f"library:{block.lane}"
            yield _stage("library", "done", "Found in the library.")
            yield EnvironmentEvent(type="environment", block=block)
            return

    pattern = SUPPORTED_PATTERNS.get(str(decision.pattern.value), "simulation")
    if decision.topic.value == "none":
        t.outcome = "text_only"
        yield _stage("plan", "degraded", "This question is answered in words. An interactive page was not made for it.")
        return

    # 4 plan and 5 plan checks (one targeted retry)
    plan: Plan | None = None
    issues: list[PlanIssue] = []
    for attempt in range(MAX_PLAN_ATTEMPTS):
        started = time.monotonic()
        yield _stage("plan", "start")
        try:
            request = prompts.plan_request(
                r.q,
                route_text,
                pattern,
                r.manifest,
                issues=issues,
                topic=str(decision.topic.value),
                use_exemplar=r.deps.use_exemplars,
            )
            raw = await r.call(request, "plan")
        except BudgetExceeded:
            t.outcome = "text_only"
            yield _stage("plan", "degraded", failchecks.get("BUDGET").student_message)
            return
        try:
            candidate = plan_module.parse(raw)
        except ValidationError as exc:
            issues = [issue_from_validation(exc)]
            t.add("plan", "invalid", started, attempt=attempt, codes=[i.code for i in issues])
            continue
        found = check(candidate, r.manifest)
        fixed = repair(candidate, found)
        if fixed is not candidate:
            found = check(fixed, r.manifest)
            candidate = fixed
        if found:
            issues = found
            t.add("plan_checks", "refused", started, attempt=attempt, codes=[i.code for i in found])
            continue
        plan = candidate
        t.add("plan_checks", "ok", started, attempt=attempt)
        break
    if plan is None:
        t.outcome = "text_only"
        yield _stage(
            "plan",
            "degraded",
            "The interactive page could not be planned safely, so you are getting the written answer.",
        )
        return
    yield PlanEvent(type="plan", draft=draft_of(plan))
    yield _stage("plan", "done")

    # 6 assemble, 7 fill
    started = time.monotonic()
    yield _stage("assemble", "start")
    fills: dict[str, str] = {}
    # A page assembled for THIS question is Compose: it was planned and built from audited Kit parts. Instantiate is kept for
    # hand-written stored Environments (fixtures); a library hit keeps the lane it was minted with.
    lane: Lane = "compose"
    scope = scope_names(plan)
    if plan.custom:
        kept = []
        for slot in plan.custom:
            text = await _fill_slot(r, slot.name, slot.purpose, scope)
            if text is not None:
                fills[slot.name] = text
                kept.append(slot)
        plan = plan.model_copy(update={"custom": kept})
    try:
        page: Assembled = assemble(plan, r.manifest, fills)
    except AssemblyGap as gap:
        t.add("assemble", "gap", started, part=gap.part)
        t.outcome = "text_only"
        yield _stage(
            "assemble",
            "degraded",
            "This interactive page needs a part that is not built yet, so you are getting the written answer.",
        )
        return
    t.add("assemble", "ok", started, slots=list(page.slots_used), lane=lane)
    yield _stage("assemble", "done")

    # 8 verify and 9 mint, store. S2: if the page with model-written fills is refused, drop the fills and verify the
    # plain assembly once (the ladder: fills, then no fills, then the written answer).
    started = time.monotonic()
    yield _stage("verify", "start")
    verify = r.deps.verify_fn or verify_environment

    async def _verify(the_plan: Plan, the_page: Assembled, the_lane: Lane):  # noqa: ANN202
        cites, earned, why = grounding(r.deps.citations, r.deps.evidence, the_plan)
        t.add("ground", "ok" if why["grounded"] else "degraded", time.monotonic(), label=earned, **{k: v for k, v in why.items() if k != "grounded"})
        return await asyncio.to_thread(
            verify,
            slug=the_plan.id,
            title=the_plan.title,
            raw_html=the_page.html,
            lane=the_lane,
            label=earned,  # type: ignore[arg-type]  # "kit-verified" or "model-checked", from `grounding`
            kit_version=r.version,
            citations=cites,
            plan_summary=the_plan.goal,
            public_origin=r.deps.public_origin,
            kit_dist=r.deps.kit_dist,
            interaction_seconds=r.deps.interaction_seconds,
            plan_models=the_plan.model_summaries(),
            evidence=r.deps.evidence,
        )

    try:
        try:
            env = await _verify(plan, page, lane)
        except VerificationFailed as first:
            if not fills:
                raise
            entry = failchecks.get(first.rule)
            t.add("verify", "refused", started, stage=first.stage, rule=first.rule, code=entry.code, retry="drop_fills")
            started = time.monotonic()
            plan = plan.model_copy(update={"custom": []})
            page = assemble(plan, r.manifest, {})
            env = await _verify(plan, page, "compose")
            lane = "compose"
    except VerificationFailed as failure:
        entry = failchecks.get(failure.rule)
        t.add(
            "verify", "refused", started, stage=failure.stage, rule=failure.rule, code=entry.code, repair=entry.repair
        )
        t.outcome = "text_only"
        yield _stage("verify", "degraded", entry.student_message)
        return
    t.add("verify", "ok", started, models=[m[0] for m in env.checked.models], layers=list(env.checked.layers))
    yield _stage("verify", "done")

    # 10 deliver (the gate re-derives the block from the stored record)
    started = time.monotonic()
    r.deps.store.put_verified(env)
    try:
        block = deliver(
            r.deps.store,
            env.env_id,
            public_origin=r.deps.public_origin,
            kit_dist=r.deps.kit_dist,
            evidence=r.deps.evidence,
        )
    except VerificationFailed as failure:
        t.add("deliver", "refused", started, rule=failure.rule)
        t.outcome = "text_only"
        yield _stage("deliver", "degraded", failchecks.get(failure.rule).student_message)
        return
    t.add("deliver", "ok", started, env_id=env.env_id[:12])
    r.deps.store.remember_question(canon, env.env_id)
    t.outcome = lane
    yield EnvironmentEvent(type="environment", block=block)


async def _fill_slot(r: _Run, name: str, purpose: str, scope: tuple[str, ...]) -> str | None:
    """Ask for one slot, check it against its contract, retry once with the named issues, else drop the slot."""
    contract = fill.contract_for(name)
    issues_msg = ""
    for attempt in range(MAX_FILL_ATTEMPTS):
        started = time.monotonic()
        try:
            code = (await r.call(prompts.fill_request(name, purpose, contract, scope, issues_msg), "fill")).strip()
        except BudgetExceeded:
            return None
        found = fill.check_fill(code, contract, scope)
        if not found:
            r.trace.add("fill", "ok", started, slot=name, attempt=attempt)
            return code
        r.trace.add("fill", "refused", started, slot=name, attempt=attempt, codes=[i.code for i in found])
        issues_msg = "Fix these problems:\n" + "\n".join(f"- [{i.code}] {i.message} {i.hint}" for i in found)
    return None
