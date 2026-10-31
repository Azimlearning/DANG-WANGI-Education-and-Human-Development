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
from typing import Literal

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
from api.pipeline.plan_checks import (
    PlanIssue,
    check,
    hands_on,
    issue_from_validation,
    needed_components,
    repair,
    retopic,
)
from api.routing.router import Route, route
from api.schema.generated import (
    CodeEvent,
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



LanePreference = Literal["kit", "balanced", "free"]
GenerationTier = Literal["standard", "heavy"]
"""Which lane leads after a Plan passes its checks (W18, D-76); see `Deps.lane_preference`."""

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
    lane_preference: LanePreference = "balanced"
    """Which lane leads once a Plan has passed its checks (W18, D-76). `kit`: Compose, and Free only when the Kit cannot take the question. `balanced`: Free leads when the
    planner says the Kit only partly fits the question, or the Plan draws no picture (no scene and no bench); Compose otherwise. `free`: Free leads for every question.
    Whenever Free leads and its page is refused, the Kit lab already planned for the question is the fallback. Only with `free_lane` on."""
    gap_log_path: Path | None = None
    """Where Kit gap records are appended (hash of the question, topic, reason; never the question). None: not logged."""
    generation_tier: GenerationTier = "standard"
    """Which model tier plans the Kit lab and writes the Free and simple pages (W20, `GENERATION_TIER`). `heavy` for a demo day: a stronger writer, larger
    output limits, more spend per question. The readers keep their own tier."""


LEAD_NOTES = {
    "partial_fit": "The Kit can only show part of this question, so a whole page is being written for it first. The Kit lab is kept as the fallback.",
    "no_picture": "The Kit lab for this would be only a graph, so a fuller drawn page is being written first. The Kit lab is kept as the fallback.",
    "free_first": "A whole page is being written for this question first. The Kit lab is kept as the fallback.",
}
"""What the build log says when the Free lane leads (W18, D-76, D-77). The pipeline's own words, never the model's."""
FALLBACK_NOTE = "That page did not pass its checks, so the Kit lab is being built instead."
RETRY_NOTE = "The first page broke a rule the checker enforces, so it is being written once more without it."
READER_RETRY_NOTE = "A second reader found a problem in the first page, so it is being written once more with the reader's notes."
BROWSER_RETRY_NOTE = "The first page failed the real-browser check, so it is being written once more with the reason."
CODE_FLUSH_CHARS = 400
"""How much generated code is gathered before it is sent on to the build log (W19, D-79): fewer, larger events, still a few a second."""


def _code(lane: str, status: str, delta: str = "", note: str | None = None, *, reset: bool = False) -> CodeEvent:
    """One step of the code view (D-79): text only, for reading; never rendered, never run."""
    return CodeEvent(type="code", lane=lane, status=status, reset=reset, delta=delta, note=note)  # type: ignore[arg-type]


async def _drain(queue: asyncio.Queue[str], call: asyncio.Task) -> AsyncIterator[str]:
    """The text a running call hands to its watcher, gathered into pieces of about CODE_FLUSH_CHARS, until the call has finished and nothing is left."""
    buffer: list[str] = []
    size = 0
    while True:
        try:
            piece = await asyncio.wait_for(queue.get(), timeout=0.25)
        except TimeoutError:
            if call.done() and queue.empty():
                if buffer:
                    yield "".join(buffer)
                return
        else:
            buffer.append(piece)
            size += len(piece)
            if size < CODE_FLUSH_CHARS:
                continue
        if buffer:
            yield "".join(buffer)
            buffer, size = [], 0
OUTSIDE_TOPICS_NOTE = "This is outside the Form 4 and 5 topics the Kit was built for, so a whole page is being written for it."
SCIENCE_DOMAINS = frozenset({"physics", "chemistry", "biology", "earth_space"})
"""The router's science domains (W19): a question in one of them with no KSSM topic still gets a Free page. `math_adjacent` and an unknown domain do not."""


def free_leads(plan: Plan, preference: str) -> str | None:
    """Why the Free lane should lead for this Plan under `preference` (W18, D-76), or None for Compose first."""
    if preference == "free":
        return "free_first"
    if preference != "balanced":
        return None
    if plan.fit == "partial":
        return "partial_fit"
    if plan.scene is None and not plan.apparatus and all(c.surface == "slider" for c in plan.controls):
        return "no_picture"
    return None


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
        self.decision: Route | None = None
        """The router's decision, once routing has run: the simple lab (W20) is written for it."""
        self.route_text = ""
        self.canon = ""
        self.extra_calls = 0
        self.free_tried = False
        """Whether the full Free page was attempted for this question (the last step tries it first when it was not)."""
        """Calls allowed beyond MAX_LLM_CALLS: only the simple lab's own allowance (SIMPLE_CALLS), granted when every other way to a lab has been used."""

    async def complete(self, request: LLMRequest, on_text: Callable[[str], None] | None = None):  # noqa: ANN201
        """The only way any layer reaches the model: it counts against the request's budget and writes a trace record. `on_text` watches the reply as it is
        written (the Free page's code, D-79)."""
        if self.trace.llm_calls >= MAX_LLM_CALLS + self.extra_calls:
            raise BudgetExceeded(request.purpose)
        self.trace.llm_calls += 1
        started = time.monotonic()
        result = await (self.deps.llm.complete(request) if on_text is None else self.deps.llm.complete(request, on_text=on_text))
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
        # W20: an unreadable reply is asked for once more (a lab that passed everything else is not thrown away over one malformed verdict).
        for attempt in range(2):
            try:
                result = await self.complete(build())
            except (BudgetExceeded, SpendCapExceeded, ProviderUnavailable, prompts.RequestTooLarge) as exc:
                self.trace.add("wording", "unavailable", started, why=type(exc).__name__)
                return None
            try:
                verdict = wording.parse_verdict(result.text)
                break
            except wording.UnusableVerdict as exc:
                self.trace.add("wording", "unreadable", started, why=str(exc)[:120], attempt=attempt)
        else:
            return None
        self.trace.add("wording", "ok" if verdict.ok else "refused", started, issues=[i[:200] for i in verdict.issues], cleared=[i[:200] for i in verdict.cleared])
        return verdict


canonical_question = library.canonical_question  # kept here too: tests and older callers import it from run


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
        components=sorted(needed_components(plan)),
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
    produced = False
    try:
        # A degraded stage ends the layers, but it is not the student's last word when the last step follows: it is held until that is known (W20).
        held: StageEvent | None = None
        async for event in _layers(r):
            if held is not None:
                yield held
                held = None
            produced = produced or event.type == "environment"
            if event.type == "stage" and event.status == "degraded":
                held = event
                continue
            yield event
        if not produced and r.trace.outcome == "text_only" and r.decision is not None and deps.free_lane and deps.wording_check:
            # W20 (D-80): every question that reached routing ends with a lab made for it. Whatever stopped the Kit lab, the full page is tried if it was not,
            # then a simpler page, each with its own call allowance. Only the spend caps (and a provider that is down) can still stop it.
            if held is not None:
                yield _stage(held.layer, "degraded", _not_final(held.note))
                held = None
            async for event in _last_resort(r):
                yield event
        if held is not None:
            yield held
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
    r.decision, r.route_text, r.canon = decision, route_text, canon
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
        if r.deps.free_lane and r.deps.lane_preference != "kit" and str(decision.domain.value) in SCIENCE_DOMAINS:
            # W19 (D-76): a science question outside the Form 4 and 5 topics the Kit was built for (the Moon's phases): no Kit Plan can fit it, so the Free lane
            # writes a whole page for it directly. A refused page is the written answer, as before.
            t.add("lane", "free_only", time.monotonic(), domain=str(decision.domain.value))
            yield _stage("plan", "done", OUTSIDE_TOPICS_NOTE)
            async for event in _no_kit_page(
                r,
                canon=canon,
                route_text=route_text,
                decision=decision,
                reason="no_kssm_topic",
                layer="plan",
                note="This question is answered in words. An interactive page was not made for it.",
            ):
                yield event
            return
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
                tier=r.deps.generation_tier,
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
        fixed = repair(retopic(candidate, r.manifest, found), found)
        if fixed is not candidate:
            if fixed.topic != candidate.topic:
                t.add("plan", "retopic", started, routed=candidate.topic, planned=fixed.topic)
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
                if candidate.fit == "partial" and r.deps.free_lane and r.deps.lane_preference != "kit":
                    # W19: the planner said the Kit only partly fits, and the reader agrees its words do not answer the question. A second plan would cost a
                    # full plan call to make another near miss; the Free lane, which leads for a partial fit anyway, is tried at once.
                    t.add("plan", "skip_retry", started, why="partial fit refused by the reader")
                    break
                continue
            wording_ok = verdict is not None
        t.add("plan_checks", "ok", started, attempt=attempt, wording="checked" if wording_ok else "not checked", parts=[a.kind for a in candidate.apparatus])
        plan = candidate
        break
    if plan is None:
        if issues and all(i.code == failchecks.get("WORDING").code for i in issues) and (not r.deps.free_lane or r.deps.lane_preference == "kit"):
            # Under the `kit` preference: the Kit CAN express this question and the second reader refused the model's prose twice, so it goes to the written answer
            # (a Free page would be a step down for a question the Kit could take). Under `balanced` and `free` (W19, D-76) it falls through to the Free lane below,
            # which has its own second reading.
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
    # 5a hands on (W20, D-80): every control the student varies is operated on the drawing. One the Plan left as a bare slider gets a graph whose point is
    # dragged, made by code from the Plan's own models and readouts; the result is checked again and kept only if every check still passes.
    upgraded = hands_on(plan, r.manifest)
    if upgraded is not plan:
        if check(upgraded, r.manifest):
            t.add("plan", "hands_on_skipped", time.monotonic(), why="the added graph did not pass the plan checks")
        else:
            t.add("plan", "hands_on", time.monotonic(), graphs=[g.x for g in upgraded.graphs[len(plan.graphs):]])
            plan = upgraded

    # 5b which lane leads (W18, D-76). With the Free lane on, a Plan the planner itself calls a partial fit, or one that draws no picture, goes to the Free lane first
    # (by preference, every Plan), and this Plan is kept as the fallback: if the Free page is refused, the Kit lab below is built as before. Nothing is lost.
    lead = free_leads(plan, r.deps.lane_preference) if r.deps.free_lane else None
    if lead is not None:
        t.add("lane", "free_first", time.monotonic(), why=lead, missing=(plan.missing or "")[:200])
        yield _stage("plan", "done", LEAD_NOTES.get(lead, LEAD_NOTES["free_first"]))
        produced = False
        async for event in _free_page(r, canon=canon, route_text=route_text, decision=decision, reason=f"free_first:{lead}", fallback=True):
            produced = produced or event.type == "environment"
            yield event
        if produced:
            return
        if lead == "partial_fit" and r.deps.wording_check:
            # W20 (D-81): the planner said the Kit only partly fits, so the Kit lab would answer a nearby question (a syringe for quantum physics). A simple lab on
            # the question itself comes first; the Kit lab is the fallback only if that fails too.
            async for event in _simple_page(r, final=False):
                produced = produced or event.type == "environment"
                yield event
            if produced:
                return
        t.add("lane", "kit_fallback", time.monotonic(), why=lead)
        t.outcome = "unknown"  # the Kit lab decides the outcome now
    yield PlanEvent(type="plan", draft=draft_of(plan))
    yield _stage("plan", "done", f"Planned with the Kit: {len(needed_components(plan))} audited parts, {len(plan.models)} science model{'s' if len(plan.models) != 1 else ''}.")

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
    yield _stage("assemble", "done", "Assembled the page from the Kit's parts. It is checked in a real browser before you see it.")
    # The assembled page in the code view (D-79): text only. The Kit's assembler writes it in one step from the Plan, so it arrives whole, not typed out.
    yield _code("compose", "unchecked", page.html, note="Assembled from the Kit's parts in one step: no model writes this code. Checking it now.", reset=True)

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
            yield _code("compose", "unchecked", page.html, note="Refused with the model-written slots; checking it again without them.", reset=True)
            env = await _verify(plan, page, "compose")
            lane = "compose"
    except VerificationFailed as failure:
        entry = failchecks.get(failure.rule)
        t.add(
            "verify", "refused", started, stage=failure.stage, rule=failure.rule, code=entry.code, repair=entry.repair
        )
        yield _code("compose", "refused", note=f"Refused in the browser: {failure.rule}.")
        t.outcome = "text_only"
        yield _stage("verify", "degraded", entry.student_message)
        return
    t.add("verify", "ok", started, models=[m[0] for m in env.checked.models], layers=list(env.checked.layers))
    yield _code("compose", "passed", note="Passed every check. This exact code now runs in the lab.")
    yield _stage("verify", "done", "Passed: every number traced to a science model, every control swept, every handle and mass dragged by mouse and finger, in a 480 px wide browser.")

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
        # The topic head is unsure (or says none): a question that names a stored Environment (D-59) is still answered from the library.
        named = library.match_by_name(decision.english or r.q, r.deps.store.all_topic_entries())
        if named is None:
            return
        missing = library.uncovered(decision.english or r.q, named)
        if missing:
            # W19: the lab shares words with the question but does not answer it (the Moon's phases are not Newton's cannonball): plan or write one instead.
            t.add("library", "skip", started, kind="name", plan=named["plan_id"], missing=missing[:6])
            return
        block = _gate(r, named["env_id"], "name", started)
        if block is None:
            return
        t.add("library", "hit", started, kind="name", env_id=named["env_id"][:12], plan=named["plan_id"])
        async for event in _serve(r, block, named["note"]):
            yield event
        return
    entries = r.deps.store.topic_entries(str(topic.value))
    if not entries:
        return
    _note_topic(r, topic)
    chosen = library.best_entry(decision.english or r.q, entries)
    missing = library.uncovered(decision.english or r.q, chosen)
    if missing:
        # W19: the right topic, but the nearest lab does not cover what was asked: plan or write one instead.
        t.add("library", "skip", started, kind="topic", plan=chosen["plan_id"], missing=missing[:6])
        return
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
    r: _Run, *, canon: str, route_text: str, decision: Route, reason: str, fallback: bool = False
) -> AsyncIterator[StreamEvent]:
    """The Free lane (D-07, D-41). One whole page written by a model, then the checks it can face: the L0 scan and post-process rules (cheap, before any more
    money is spent), a second model reading its words AND formulas (required: it is the only content check a Free page gets), and the real-browser run. The
    label is `model-checked` with an unchecked citation and the lane is `free`; it never reaches `kit-verified` or `canonical`. Any failure is the written answer."""
    t = r.trace
    started = time.monotonic()
    r.free_tried = True
    _allow(r, 4)  # its own room (W20): two pages, each with its reading, whatever the Kit attempts used
    yield _stage("assemble", "start", "Writing a whole page for this question. A page written this way is checked less than the others.")

    def degrade(rule: str, layer: str = "assemble", **detail: object) -> StreamEvent:
        entry = failchecks.get(rule)
        t.add("free", "refused", started, rule=rule, code=entry.code, **detail)
        if fallback:
            # A Kit lab is planned and follows (W18): no "written answer only" note, just the next stage.
            return _stage("assemble", "start", FALLBACK_NOTE)
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
        free_req = prompts.free_request(r.q, route_text, tier=r.deps.generation_tier)
        reading_req = prompts.free_wording_request(topic, stand_in, passage)
    except prompts.RequestTooLarge as exc:
        yield degrade("FREE_REPLY", note=str(exc)[:200])
        return
    if r.trace.llm_calls + 2 > MAX_LLM_CALLS + r.extra_calls or not r.deps.llm.would_fit([free_req, reading_req]):
        yield degrade("BUDGET", why="the page and its reading would not both fit")
        return
    # One page, and at most one more (W19, W20): when the cheap checks (a complete document, the scan, post-processing, a length the reader can take) or the
    # second reader refuse it, the generator is told the exact reason once, in our checkers' words or the reader's, if the request still has room for a page
    # and its reading. A small error (an unbalanced label) is easier to fix than to start again from a simpler page.
    fix: str | None = None
    retry_note = RETRY_NOTE
    page: free_module.Page | None = None
    env: VerifiedEnvironment | None = None
    subject, notes = topic, passage if decision.topic.source == "local" else "(none)"
    for attempt in range(2):
        if attempt == 1:
            free_req = prompts.free_request(r.q, route_text, fix=fix, tier=r.deps.generation_tier)
            if r.trace.llm_calls + 2 > MAX_LLM_CALLS + r.extra_calls or not r.deps.llm.would_fit([free_req, reading_req]):
                yield degrade("BUDGET", why="no room for a second page and its reading")
                return
            yield _stage("assemble", "start", retry_note)
        # The page streams into the build log as it is written (D-79): text for reading, never run. Only the verified block below is ever run.
        yield _code("free", "writing", note=None if attempt == 0 else retry_note, reset=True)
        written: asyncio.Queue[str] = asyncio.Queue()
        call = asyncio.create_task(r.complete(free_req, on_text=written.put_nowait))
        try:
            async for piece in _drain(written, call):
                yield _code("free", "writing", piece)
        finally:
            if not call.done():
                call.cancel()  # the student left: the service books what was spent
        try:
            result = call.result()
        except (BudgetExceeded, SpendCapExceeded):
            yield _code("free", "refused", note="The page could not be written: the spend limit stopped it.")
            yield degrade("BUDGET")
            return
        except ProviderUnavailable:
            # Most often the page ran past its length limit and was cut off (W19): that is a page that could not be written, not a budget.
            yield _code("free", "refused", note="The page could not be written whole (it was cut off, or the provider failed).")
            yield degrade("FREE_REPLY", why="the provider failed or the page was cut off")
            return
        read = free_module.read_reply(result.text)
        page = read if isinstance(read, free_module.Page) else None
        if page is None:
            if attempt == 0:
                fix = str(read)
                t.add("free", "retry", started, why=fix[:200])
                continue
            yield _code("free", "refused", note="The reply was not one complete web page.")
            yield degrade("FREE_REPLY", why="no complete document in the reply")
            return
        yield _code("free", "unchecked", note="Written. Now the checker scans it before anything else is spent.")
        early = postprocess.run(page.html, public_origin=r.deps.public_origin)  # no kit_version: the Free lane's own, narrower rules apply
        if isinstance(early, postprocess.PostprocessReject):
            yield _code("free", "refused", note=f"Refused by the checker: {early.reason[:160]}")
            if attempt == 0:
                fix = early.reason[:300]
                t.add("free", "retry", started, rule=early.rule, stage=early.stage, reason=early.reason[:200])
                continue
            yield degrade(early.rule, layer="verify", stage=early.stage, reason=early.reason[:200])
            return
        too_big = wording.unread(page.html)
        if too_big is not None:
            # The reader would see only part of it, and a page not read whole must not earn the claim that its words and formulas were read.
            yield _code("free", "refused", note="Too long to be read whole by the second reader.")
            if attempt == 0:
                fix = f"the page was too long to be read whole ({too_big}); keep the script under 20,000 characters and the words short"
                t.add("free", "retry", started, why="too long")
                continue
            yield degrade("FREE_REPLY", layer="verify", why=too_big)
            return
        yield _code("free", "unchecked", note="Passed the scan. A second model is now reading its words and formulas.")
        # The reader judges the page on its own subject (W19): its title, not the routed topic, which can be wrong (the Moon's phases were once filed under
        # nuclear physics, and a correct page was refused as off-topic). The routed topic's textbook notes are given only when the local router was sure of it.
        subject = page.title or topic
        verdict = await r.judge(lambda p=page, s=subject: prompts.free_wording_request(s, p.html, notes))
        if verdict is None:
            yield _code("free", "refused", note="The second reader gave no usable answer, so the page is not shown.")
            yield degrade("FREE_UNCHECKED", layer="verify")
            return
        if not verdict.ok:
            yield _code("free", "refused", note=f"The second reader found a problem: {verdict.issues[0][:160] if verdict.issues else 'no reason given'}")
            if attempt == 0:
                fix = "a second reader found these problems in its science or words: " + "; ".join(i[:200] for i in verdict.issues[:3])
                retry_note = READER_RETRY_NOTE
                t.add("free", "retry", started, why="reader", issues=[i[:200] for i in verdict.issues])
                continue
            yield degrade("WORDING", layer="verify", issues=[i[:200] for i in verdict.issues])
            return
        yield _code("free", "unchecked", note="Read and accepted. Now it runs in a real browser.")
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
            yield _code("free", "refused", note=f"Refused in the browser: {failure.rule}.")
            if attempt == 0:
                # W20 (D-81): a page refused in the browser (a slider that moves no readout, a handle that drags nothing) is written once more, told which check failed.
                fix = f"the real-browser check refused it ({failure.stage}/{failure.rule}): {failure.reason[:240]}"
                retry_note = BROWSER_RETRY_NOTE
                t.add("free", "retry", started, why="browser", rule=failure.rule)
                env = None
                continue
            if fallback:
                yield _stage("assemble", "start", FALLBACK_NOTE)
                return
            t.outcome = "text_only"
            yield _stage("verify", "degraded", entry.student_message)
            return
        break
    if page is None or env is None:  # the loop returns rather than leave without a lab; this keeps the type checker sure of it
        return
    t.add("verify", "ok", started, lane="free", layers=list(env.checked.layers))
    yield _code("free", "passed", note="Passed every check. This exact code now runs in the lab.")
    yield _stage("verify", "done", "Passed the browser run and a second reading of its words and formulas.")
    delivered = False
    async for event in _store_and_deliver(r, env, canon, "free"):
        delivered = delivered or event.type == "environment"
        yield event
    if delivered:
        t.add("free", "ok", started, env_id=env.env_id[:12])
        _log_gap(r, decision, reason, "free", env.env_id)


SIMPLE_ATTEMPTS = 3
"""How many simple pages the last step may write (W20, D-80). Each one after the first is told exactly why the one before it was refused."""
SIMPLE_CALLS = 2 * SIMPLE_ATTEMPTS
"""A page and its reading per attempt."""
SIMPLE_NOTE = "The full lab did not pass its checks, so a simpler lab is being written for your question."
SIMPLE_RETRY_NOTE = "That simple lab was refused, so it is being written again with the checker's reason."
NO_LAB_NOTE = "No lab could be made for this question this time. Try asking it in other words."


_WRITTEN_ANSWER = re.compile(r",? so you are getting the written answer(?: instead)?\.?\s*$")


def _not_final(note: str | None) -> str:
    """A refusal's note without its claim that the written answer is all the student gets: the last step is about to try for a lab (W20)."""
    reason = _WRITTEN_ANSWER.sub(".", note or "That attempt was refused.").strip()
    return f"{reason} Another lab is being written."


def _allow(r: _Run, calls: int) -> None:
    """Room for exactly `calls` more model calls from here, whatever the request has used: the last step's own allowance (W20)."""
    r.extra_calls = max(r.extra_calls, r.trace.llm_calls + calls - MAX_LLM_CALLS)


async def _last_resort(r: _Run) -> AsyncIterator[StreamEvent]:
    """W20 (D-80): the question has no lab yet. The full Free page first, if it was never tried (a Compose page refused in the browser went nowhere else), then
    the simple page. Every page still faces every check a Free page faces; nothing unchecked is shown."""
    assert r.decision is not None
    if not r.free_tried:
        produced = False
        async for event in _free_page(r, canon=r.canon, route_text=r.route_text, decision=r.decision, reason="last_resort", fallback=True):
            produced = produced or event.type == "environment"
            yield event
        if produced:
            return
    async for event in _simple_page(r):
        yield event


async def _simple_page(r: _Run, final: bool = True) -> AsyncIterator[StreamEvent]:
    """The last step (W20, D-80): a small page for the question, one or two things to drag and a few readouts (the free_simple pack), in the Free lane.
    Up to SIMPLE_ATTEMPTS pages; when a page is refused (cut off, not a document, the scan, too long to read, the second reader, the browser) the next one is
    told why, in our checkers' words or the reader's. The checks are the Free lane's, unchanged."""
    t, decision = r.trace, r.decision
    assert decision is not None
    started = time.monotonic()
    if not r.deps.wording_check:
        t.add("simple", "skipped", started, why="no second reader is configured")
        return
    _allow(r, SIMPLE_CALLS)
    t.outcome = "unknown"
    topic = str(decision.topic.value)
    passage = prompts.passage_for(r.deps.citations, topic=topic)
    notes = passage if decision.topic.source == "local" else "(none)"
    fix: str | None = None
    yield _stage("assemble", "start", SIMPLE_NOTE)
    for attempt in range(SIMPLE_ATTEMPTS):
        if attempt:
            t.add("simple", "retry", started, attempt=attempt, why=(fix or "")[:200])
            yield _stage("assemble", "start", SIMPLE_RETRY_NOTE)
        try:
            request = prompts.simple_request(r.q, r.route_text, fix, tier=r.deps.generation_tier)
        except prompts.RequestTooLarge as exc:
            t.add("simple", "refused", started, why=str(exc)[:200])
            break
        if not r.deps.llm.would_fit([request]):
            t.add("simple", "refused", started, rule="BUDGET", why="the monthly spend cap")
            break
        yield _code("free", "writing", note=SIMPLE_NOTE if attempt == 0 else SIMPLE_RETRY_NOTE, reset=True)
        written: asyncio.Queue[str] = asyncio.Queue()
        call = asyncio.create_task(r.complete(request, on_text=written.put_nowait))
        try:
            async for piece in _drain(written, call):
                yield _code("free", "writing", piece)
        finally:
            if not call.done():
                call.cancel()
        try:
            result = call.result()
        except (BudgetExceeded, SpendCapExceeded):
            yield _code("free", "refused", note="The page could not be written: the spend limit stopped it.")
            t.add("simple", "refused", started, rule="BUDGET")
            break
        except ProviderUnavailable:
            fix = "the page was cut off before it ended; write a shorter page"
            yield _code("free", "refused", note="The page was cut off, or the provider failed.")
            continue
        read = free_module.read_reply(result.text)
        if not isinstance(read, free_module.Page):
            fix = str(read)
            yield _code("free", "refused", note=f"The reply was not a complete lab: {fix[:160]}")
            continue
        page = read
        early = postprocess.run(page.html, public_origin=r.deps.public_origin)
        if isinstance(early, postprocess.PostprocessReject):
            fix = early.reason[:300]
            yield _code("free", "refused", note=f"Refused by the checker: {early.reason[:160]}")
            continue
        if wording.unread(page.html) is not None:
            fix = "the page was too long to be read whole; keep the script under 8,000 characters and the words short"
            yield _code("free", "refused", note="Too long to be read whole by the second reader.")
            continue
        yield _code("free", "unchecked", note="Passed the scan. A second model is now reading its words and formulas.")
        verdict = await r.judge(lambda p=page: prompts.free_wording_request(p.title or topic, p.html, notes))
        if verdict is None:
            yield _code("free", "refused", note="The second reader gave no usable answer, so the page is not shown.")
            t.add("simple", "refused", started, rule="FREE_UNCHECKED")
            continue
        if not verdict.ok:
            fix = "a second reader found these problems in its science or words: " + "; ".join(i[:200] for i in verdict.issues[:3])
            yield _code("free", "refused", note=f"The second reader found a problem: {verdict.issues[0][:160] if verdict.issues else 'no reason given'}")
            continue
        yield _code("free", "unchecked", note="Read and accepted. Now it runs in a real browser.")
        yield _stage("verify", "start")
        verify = r.deps.verify_fn or verify_environment
        try:
            env = await asyncio.to_thread(
                verify,
                slug=free_module.slug_for(r.canon),
                title=page.title,
                raw_html=page.html,
                lane="free",
                label="model-checked",
                kit_version=r.version,
                citations=[UNCHECKED_CITATION],
                plan_summary=f"A simple page written whole by a model, the last step when no fuller lab passed its checks (topic {decision.topic.value}).",
                public_origin=r.deps.public_origin,
                kit_dist=r.deps.kit_dist,
                interaction_seconds=r.deps.interaction_seconds,
                plan_models=None,
                evidence=r.deps.evidence,
                wording_checked=True,
            )
        except VerificationFailed as failure:
            fix = f"the browser check refused it ({failure.stage}/{failure.rule}): {failure.reason[:240]}"
            t.add("simple", "refused", started, stage=failure.stage, rule=failure.rule)
            yield _code("free", "refused", note=f"Refused in the browser: {failure.rule}.")
            continue
        yield _code("free", "passed", note="Passed every check. This exact code now runs in the lab.")
        yield _stage("verify", "done", "A simple lab, written for your question, passed the browser run and a second reading of its words and formulas.")
        delivered = False
        async for event in _store_and_deliver(r, env, r.canon, "free"):
            delivered = delivered or event.type == "environment"
            yield event
        if delivered:
            t.add("simple", "ok", started, attempt=attempt, env_id=env.env_id[:12])
            _log_gap(r, decision, "simple", "free", env.env_id)
            return
        break
    if not final:
        # A Kit lab follows (W20, D-81): no "no lab" note, just the next stage.
        t.add("simple", "refused", started, then="kit_fallback")
        yield _stage("assemble", "start", FALLBACK_NOTE)
        return
    t.outcome = "text_only"
    _log_gap(r, decision, "simple", "text_only")
    yield _stage("verify", "degraded", NO_LAB_NOTE)


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
