"""The pipeline orchestrator: the layers of D-23 in order, on whatever LLM service it is given (fakes by default).

    intake -> route -> look up -> explain (text first) -> plan -> plan checks -> assemble -> fill -> verify -> mint, store, gate -> deliver

Every layer writes a trace record. A layer either passes on, repairs deterministically, asks the model once more with named issues, or degrades.
The degrade ladder never leaves a blank screen: Instantiate (a plan assembled with no model-written code), Compose (with checked slot fills), the labelled
Free lane (a whole model-written page, only when `Deps.free_lane` is on; D-41), then the written answer with a plain note.
The text answer streams first, so a failed Environment still leaves a useful answer.

L4 (D-41): when `Deps.wording_check` is on, a second model reads the Plan's words inside the plan retry loop; the layer `wording` is claimed only for a judge
that answered ok. Every question the Kit cannot take is appended to the Kit gap log, whether or not the Free lane is on.

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

from api import kitmanifest, postprocess
from api.core.errors import ProviderUnavailable, SpendCapExceeded, SynapseError, envelope_from_exception
from api.evidence.registry import CitationBook
from api.kit import latest_version
from api.llm.service import LLMService
from api.llm.types import LLMRequest
from api.models.exam import event_for as exam_event_for
from api.models.misconceptions import default_matcher
from api.models.probes import basis_of, probe_for
from api.pipeline import failchecks, fill, gaplog, library, prompts, wording
from api.pipeline import free as free_module
from api.pipeline import plan as plan_module
from api.pipeline.assemble import Assembled, AssemblyGap, assemble, scope_names
from api.pipeline.grounding import UNCHECKED_CITATION, grounding
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
    ProbeEvent,
    StageEvent,
    StreamErrorEvent,
    StreamEvent,
    TextDeltaEvent,
)
from api.sse import split_text
from api.verify.gate import deliver
from api.verify.mint import Evidence, VerificationFailed, VerifiedEnvironment, verify_environment
from api.verify.store import ConflictingRecord, SqliteEnvironmentStore

log = logging.getLogger(__name__)

MAX_LLM_CALLS = 8
"""Raised from 6 for L4 and the Free lane (D-41): explain, a possible route fallback, two plans each followed by a wording check, then one Free page and its
wording check is 8. Slot fills draw on the same budget and are dropped, not retried, when it is spent."""
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
    wording_check: bool = False
    """L4 (D-41): a second model reads the Plan's words before the page is built. Off by default and off in fake mode: a fake judge examined nothing, and
    the layer `wording` is claimed only for a judge that answered. The API turns it on in live mode."""
    free_lane: bool = False
    """The labelled Free lane (D-07, D-41): a question the Kit cannot express may get a whole model-written page, `model-checked` at most. Off by default."""
    gap_log_path: Path | None = None
    """Where Kit gap records are appended (hash of the question, topic, reason; never the question). None: not logged."""


def _issue_notes(issues: list[PlanIssue]) -> list[str]:
    """What the plan checks said, short, for the trace: a code alone cannot tell you WHICH model the planner invented or which binding was wrong. The text
    is ours (the checks' messages), not the model's reply, and carries no student text."""
    return [f"{i.code} {i.path}: {i.message}"[:240] for i in issues[:6]]


class BudgetExceeded(Exception):
    pass


class _Run:
    def __init__(self, question: str, deps: Deps):
        self.q = " ".join(question.split())
        self.deps = deps
        self.request_id = uuid.uuid4().hex
        self.trace = Trace(self.request_id, hashlib.sha256(self.q.encode()).hexdigest()[:16])
        self.answer = ""
        """The written answer that streamed for this request; kept with the question so a repeat needs no model call for the words either."""
        self.topic: str | None = None
        """The topic the router settled on, when it is sure enough to offer a topic-specific practice question (W5c)."""
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

    async def judge(self, build: Callable[[], LLMRequest]) -> wording.WordingVerdict | None:
        """One L4 call. None means there is NO usable verdict (over the call budget or the cap, the provider unreachable, a request too large to send, or an
        unreadable reply), and the caller must not claim the layer. A usable verdict, pass or refusal, is returned as read. A provider that REJECTS the
        request (balance, key) is not swallowed: that is the operator's problem and stops the request, as it does for every other call."""
        started = time.monotonic()
        try:
            result = await self.complete(build())
        except (BudgetExceeded, SpendCapExceeded, ProviderUnavailable, prompts.RequestTooLarge) as exc:
            self.trace.add("wording", "unavailable", started, why=type(exc).__name__)
            return None
        try:
            verdict = wording.parse_verdict(result.text)
        except wording.UnusableVerdict as exc:
            self.trace.add("wording", "unreadable", started, why=str(exc)[:120])
            return None
        self.trace.add("wording", "ok" if verdict.ok else "refused", started, issues=[i[:200] for i in verdict.issues])
        return verdict


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
    if r.trace.outcome not in ("refused", "error"):
        probe = _probe_event(r.q)
        if probe is not None:
            yield probe
        practice = exam_event_for(r.topic) if r.topic else None
        if practice is not None:
            yield practice
    yield DoneEvent(type="done")


def _note_topic(r: _Run, topic) -> None:  # noqa: ANN001
    """Remember the topic only when it can be trusted: a local guess below the library's confidence bar would offer a practice question about the wrong chapter."""
    if topic.value == "none" or (topic.source == "local" and topic.confidence < library.INSTANTIATE_MIN_CONFIDENCE):
        return
    r.topic = str(topic.value)


def _probe_event(question: str) -> ProbeEvent | None:
    """The optional follow-up question (W5a): plain text from data/probes.json, no model call, never HTML."""
    found = probe_for(question)
    if found is None:
        return None
    probe, source_verified = found
    return ProbeEvent(
        type="probe",
        id=probe.id,
        question=probe.question,
        options=list(probe.options),
        correct=probe.correct,
        explanation=probe.explanation,
        basis=basis_of(source_verified),
    )


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

    # 0b the library, before anything is paid (D-42). A question asked before, or one the LOCAL router recognises with enough confidence, is answered with a
    # stored Environment and the words stored with it: no routing call, no explanation call, no planning, no verification run. Every hit goes through the
    # gate again; a refusal falls through to generating a new one.
    canon = canonical_question(r.q)
    served = False
    async for event in _from_library(r, canon):
        served = served or event.type == "environment"
        yield event
    if served:
        return

    # 1 route
    started = time.monotonic()
    yield _stage("route", "start")
    decision = await route(r.q, llm=r if r.deps.use_router else None)  # type: ignore[arg-type]  # _Run exposes the LLMService.complete shape
    t.add(
        "route", "ok", started, **{h: {"value": d.value, "source": d.source} for h, d in decision.decisions().items()}
    )
    route_text = _route_summary(decision)
    _note_topic(r, decision.topic)
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
        explained = False
    else:
        explained = True
    for chunk in split_text(answer):
        yield TextDeltaEvent(type="text_delta", text=chunk)
    r.answer = answer if explained else ""  # a placeholder about the budget is not an answer, and is not kept with the question
    t.add("explain", "ok", started)
    yield _stage("explain", "done")

    pattern = SUPPORTED_PATTERNS.get(str(decision.pattern.value), "simulation")
    if decision.topic.value == "none":
        t.outcome = "text_only"
        yield _stage("plan", "degraded", "This question is answered in words. An interactive page was not made for it.")
        return

    # 4 plan and 5 plan checks (one targeted retry)
    plan: Plan | None = None
    issues: list[PlanIssue] = []
    wording_ok = False  # True only when a judge answered ok for the Plan that was accepted
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
        except prompts.RequestTooLarge as exc:
            # Raised before anything is sent: nothing was spent. The student gets the written answer instead of an internal error.
            t.add("plan", "request_too_large", started, attempt=attempt, note=str(exc)[:200])
            t.outcome = "text_only"
            yield _stage(
                "plan",
                "degraded",
                "The interactive page could not be planned safely, so you are getting the written answer.",
            )
            return
        try:
            candidate = plan_module.parse(raw)
        except ValidationError as exc:
            issues = [issue_from_validation(exc)]
            t.add("plan", "invalid", started, attempt=attempt, codes=[i.code for i in issues], issues=_issue_notes(issues))
            continue
        found = check(candidate, r.manifest)
        fixed = repair(candidate, found)
        if fixed is not candidate:
            found = check(fixed, r.manifest)
            candidate = fixed
        if found:
            issues = found
            t.add(
                "plan_checks",
                "refused",
                started,
                attempt=attempt,
                codes=[i.code for i in found],
                issues=_issue_notes(found),
                models=[m.model for m in candidate.models],
            )
            continue
        if r.deps.wording_check:
            # L4 (D-41): a second model reads the Plan's words. A refusal goes back to the planner like a plan check; no verdict (the judge was unavailable
            # or unreadable) lets the Plan through WITHOUT the layer being claimed.
            passage = prompts.passage_for(r.deps.citations, ids=candidate.citation_ids, topic=candidate.topic)
            verdict = await r.judge(lambda c=candidate, p=passage: prompts.wording_request(c, p))
            if verdict is not None and not verdict.ok:
                entry = failchecks.get("WORDING")
                issues = [PlanIssue(entry.code, "wording", text, entry.model_hint) for text in verdict.issues]
                t.add("plan_checks", "refused", started, attempt=attempt, codes=[entry.code], issues=_issue_notes(issues))
                continue
            wording_ok = verdict is not None
        t.add("plan_checks", "ok", started, attempt=attempt, wording="checked" if wording_ok else "not checked")
        plan = candidate
        break
    if plan is None:
        if issues and all(i.code == failchecks.get("WORDING").code for i in issues):
            # The Kit CAN express this question; the second reader refused the model's prose twice. A whole Free page would be a step down to a less-checked
            # lane for a question the Kit could take, and the refusal is not a Kit gap, so it goes to the written answer and is logged as what it is.
            _log_gap(r, decision, "wording_refused", "text_only")
            t.outcome = "text_only"
            yield _stage("plan", "degraded", failchecks.get("WORDING").student_message)
            return
        reason = "plan_failed:" + ",".join(sorted({i.code for i in issues})[:6]) if issues else "plan_failed"
        async for event in _no_kit_page(
            r,
            canon=canon,
            route_text=route_text,
            decision=decision,
            reason=reason,
            layer="plan",
            note="The interactive page could not be planned safely, so you are getting the written answer.",
        ):
            yield event
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
        async for event in _no_kit_page(
            r,
            canon=canon,
            route_text=route_text,
            decision=decision,
            reason=f"assembly_gap:{gap.part}",
            layer="assemble",
            note="This interactive page needs a part that is not built yet, so you are getting the written answer.",
        ):
            yield event
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
            # The judge read the Plan's words. A slot fill is code the model wrote AFTER that reading and it can print text (`Synapse.text`), so a page that
            # has any fill was not read whole and does not claim the layer.
            wording_checked=wording_ok and not the_plan.custom,
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

    async for event in _store_and_deliver(r, env, canon, lane):
        yield event


async def _store_and_deliver(r: _Run, env: VerifiedEnvironment, canon: str, lane: Lane) -> AsyncIterator[StreamEvent]:
    """10 deliver: store the minted Environment, then let the gate re-derive the block from the stored record. Shared by Compose and the Free lane."""
    t = r.trace
    started = time.monotonic()
    try:
        r.deps.store.put_verified(env)
    except ConflictingRecord:
        # The page just made is byte for byte one that is already stored under another claim (a library Environment, for example, when a planner reproduces
        # a hand-written Plan). A stored Environment is never replaced, and the stored claim stands: it is delivered through the gate below, which refuses it
        # if it was withdrawn, is stale or no longer proves.
        t.add("deliver", "existing", started, env_id=env.env_id[:12], stored_lane=r.deps.store.get_record(env.env_id).lane)  # type: ignore[union-attr]
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
    r.deps.store.remember_question(canon, env.env_id, r.answer or None)
    t.outcome = block.lane
    yield EnvironmentEvent(type="environment", block=block)


def _gate(r: _Run, env_id: str, kind: str, started: float):  # noqa: ANN202
    """The block for a stored Environment through the delivery gate, or None (with a trace record) when the gate refuses it."""
    try:
        return deliver(
            r.deps.store, env_id, public_origin=r.deps.public_origin, kit_dist=r.deps.kit_dist, evidence=r.deps.evidence
        )
    except VerificationFailed as failure:
        r.trace.add("library", "refused", started, kind=kind, rule=failure.rule)
        return None


async def _from_library(r: _Run, canon: str) -> AsyncIterator[StreamEvent]:
    """Serve a stored Environment with NO model call, or yield nothing (D-42).

    (a) The same canonical question asked before: its Environment and the written answer kept with it.
    (b) A topic the LOCAL router recognises with at least `INSTANTIATE_MIN_CONFIDENCE`, when the seeded library has an Environment for it: the nearest one to
    the question and the hand-written Plan's own note as the words. The router is asked without the model fallback, so a low-confidence or unknown topic
    simply falls through to the normal pipeline. Either way the gate re-checks the stored row, so a stale, tampered or withdrawn Environment is not served."""
    t = r.trace
    started = time.monotonic()
    entry = r.deps.store.lookup_question_entry(canon)
    if entry is not None:
        block = _gate(r, entry[0], "question", started)
        if block is not None:
            text = entry[1] or block.planSummary
            t.add("library", "hit", started, kind="question", env_id=entry[0][:12], words="kept" if entry[1] else "plan summary")
            async for event in _serve(r, block, text):
                yield event
            return
    if not r.deps.use_router:
        return
    decision = await route(r.q, llm=None)
    topic = decision.topic
    if topic.source != "local" or topic.value == "none" or topic.confidence < library.INSTANTIATE_MIN_CONFIDENCE:
        return
    entries = r.deps.store.topic_entries(str(topic.value))
    if not entries:
        return
    _note_topic(r, topic)
    chosen = library.best_entry(r.q, entries)
    block = _gate(r, chosen["env_id"], "topic", started)
    if block is None:
        return
    t.add("route", "ok", started, topic={"value": topic.value, "source": topic.source}, library="topic")
    t.add("library", "hit", started, kind="topic", env_id=chosen["env_id"][:12], confidence=topic.confidence)
    async for event in _serve(r, block, chosen["note"]):
        yield event


async def _serve(r: _Run, block, text: str) -> AsyncIterator[StreamEvent]:  # noqa: ANN001
    for chunk in split_text(text):
        yield TextDeltaEvent(type="text_delta", text=chunk)
    r.trace.outcome = f"library:{block.lane}"
    yield _stage("library", "done", "Found in the library.")
    yield EnvironmentEvent(type="environment", block=block)


def _log_gap(r: _Run, decision: Route, reason: str, outcome: str, env_id: str | None = None) -> None:
    gaplog.record(
        r.deps.gap_log_path,
        question_sha256=r.trace.question_sha256,
        topic=str(decision.topic.value),
        domain=str(decision.domain.value),
        pattern=str(decision.pattern.value),
        reason=reason,
        outcome=outcome,
        env_id=env_id,
    )


async def _no_kit_page(
    r: _Run, *, canon: str, route_text: str, decision: Route, reason: str, layer: str, note: str
) -> AsyncIterator[StreamEvent]:
    """The Kit cannot take this question (an assembly gap, or a Plan that could not be made to pass). The reason is logged as a Kit gap either way. With the
    Free lane on, try one whole page; otherwise, or if that fails, the written answer (the text has already streamed)."""
    t = r.trace
    if not r.deps.free_lane:
        _log_gap(r, decision, reason, "text_only")
        t.outcome = "text_only"
        yield _stage(layer, "degraded", note)
        return
    produced = False
    try:
        async for event in _free_page(r, canon=canon, route_text=route_text, decision=decision, reason=reason):
            produced = produced or event.type == "environment"
            yield event
    except BaseException:
        _log_gap(r, decision, reason, "error")  # a provider rejection or a bug ends the request, but the gap and any money spent are still on record
        raise
    if not produced:
        _log_gap(r, decision, reason, "text_only")


async def _free_page(
    r: _Run, *, canon: str, route_text: str, decision: Route, reason: str
) -> AsyncIterator[StreamEvent]:
    """The Free lane (D-07, D-41). One whole page written by a model, then the checks it can face: the L0 scan and post-process rules (cheap, before any more
    money is spent), a second model reading its words AND formulas (required: it is the only content check a Free page gets), and the real-browser run. The
    label is `model-checked` with an unchecked citation and the lane is `free`; it never reaches `kit-verified` or `canonical`. Any failure is the written answer."""
    t = r.trace
    started = time.monotonic()
    yield _stage("assemble", "start", "Writing a whole page for this question. A page written this way is checked less than the others.")

    def degrade(rule: str, layer: str = "assemble", **detail: object) -> StreamEvent:
        entry = failchecks.get(rule)
        t.add("free", "refused", started, rule=rule, code=entry.code, **detail)
        t.outcome = "text_only"
        return _stage(layer, "degraded", entry.student_message)

    if not r.deps.wording_check:
        # A Free page is shown only after a second reader has read it, and no reader is configured (fake mode never sets one). Nothing has been spent yet.
        yield degrade("FREE_UNCHECKED", why="the wording check is not turned on")
        return
    topic = str(decision.topic.value)
    passage = prompts.passage_for(r.deps.citations, topic=topic)
    # A page is worth nothing unless it can also be read, so BOTH calls must fit before the first is paid for: two calls left in the request's budget, and
    # room under the caps for the page and for a reading of a typical-sized page (cost-auditor 2026-10-22).
    stand_in = "<p>" + "x" * 6000 + "</p><script>" + "y" * 3000 + "</script>"
    try:
        free_req = prompts.free_request(r.q, route_text)
        reading_req = prompts.free_wording_request(topic, stand_in, passage)
    except prompts.RequestTooLarge as exc:
        yield degrade("FREE_REPLY", note=str(exc)[:200])
        return
    if r.trace.llm_calls + 2 > MAX_LLM_CALLS or not r.deps.llm.would_fit([free_req, reading_req]):
        yield degrade("BUDGET", why="the page and its reading would not both fit")
        return
    try:
        result = await r.complete(free_req)
    except (BudgetExceeded, SpendCapExceeded, ProviderUnavailable):
        yield degrade("BUDGET")
        return
    page = free_module.parse_reply(result.text)
    if page is None:
        yield degrade("FREE_REPLY", why="no complete document in the reply")
        return

    early = postprocess.run(page.html, public_origin=r.deps.public_origin)  # no kit_version: the Free lane's own, narrower rules apply
    if isinstance(early, postprocess.PostprocessReject):
        yield degrade(early.rule, layer="verify", stage=early.stage)
        return
    too_big = wording.unread(page.html)
    if too_big is not None:
        # The reader would see only part of it, and a page not read whole must not earn the claim that its words and formulas were read.
        yield degrade("FREE_REPLY", layer="verify", why=too_big)
        return

    verdict = await r.judge(lambda: prompts.free_wording_request(topic, page.html, passage))
    if verdict is None:
        yield degrade("FREE_UNCHECKED", layer="verify")
        return
    if not verdict.ok:
        yield degrade("WORDING", layer="verify", issues=[i[:200] for i in verdict.issues])
        return

    yield _stage("verify", "start")
    verify = r.deps.verify_fn or verify_environment
    try:
        env = await asyncio.to_thread(
            verify,
            slug=free_module.slug_for(canon),
            title=page.title,
            raw_html=page.html,
            lane="free",
            label="model-checked",
            kit_version=r.version,
            citations=[UNCHECKED_CITATION],
            plan_summary=f"A page written whole by a model for a question the Kit could not express (topic {decision.topic.value}).",
            public_origin=r.deps.public_origin,
            kit_dist=r.deps.kit_dist,
            interaction_seconds=r.deps.interaction_seconds,
            plan_models=None,
            evidence=r.deps.evidence,
            wording_checked=True,
        )
    except VerificationFailed as failure:
        entry = failchecks.get(failure.rule)
        t.add("verify", "refused", started, stage=failure.stage, rule=failure.rule, code=entry.code, lane="free")
        t.outcome = "text_only"
        yield _stage("verify", "degraded", entry.student_message)
        return
    t.add("verify", "ok", started, lane="free", layers=list(env.checked.layers))
    yield _stage("verify", "done")
    delivered = False
    async for event in _store_and_deliver(r, env, canon, "free"):
        delivered = delivered or event.type == "environment"
        yield event
    if delivered:
        t.add("free", "ok", started, env_id=env.env_id[:12])
        _log_gap(r, decision, reason, "free", env.env_id)


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
