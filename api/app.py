"""The FastAPI application factory. Fakes by default: with SYNAPSE_LLM_MODE=fake nothing here touches the network."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, ConfigDict, Field

from api import postprocess
from api.core.errors import HTTP_STATUS, BadRequest, NotFound, RateLimited, SynapseError, envelope_from_exception
from api.core.settings import Settings, load_settings
from api.export import ExportRefused, standalone_page
from api.kit import built_versions
from api.limits import ConcurrencyGate, RateLimiter
from api.llm.factory import build_ledger, build_llm_service
from api.llm.service import LLMService
from api.pipeline.run import Deps
from api.pipeline.run import run as run_pipeline
from api.schema.generated import (
    AskRequest,
    DoneEvent,
    ErrorEnvelope,
    FieldIssue,
    StreamErrorEvent,
    StreamEvent,
)
from api.seed import open_store
from api.static import mount_kit
from api.verify.gate import deliver
from api.verify.mint import VerificationFailed, kit_bundle_sha256
from api.verify.store import SqliteEnvironmentStore

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500


class _Note(BaseModel):
    """The body of a flag or a withdrawal: one short note."""

    model_config = ConfigDict(extra="forbid", strict=True)
    note: str = Field(min_length=1, max_length=240)


def evidence_for(settings: Settings):  # noqa: ANN201
    """The corpus-backed evidence source, or None when no corpus is configured (then `kit-verified` is unreachable, by design)."""
    if settings.corpus_dir is None:
        return None
    from api.evidence.citations import Evidence
    from api.evidence.corpus import Corpus

    return Evidence(Corpus.load(settings.corpus_dir))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Synapse v4 API", version="0.1.0")
    app.state.settings = settings
    app.state.store = open_store(settings)
    app.state.ledger = build_ledger(settings)
    app.state.rate = RateLimiter(settings.rate_limit_per_minute)
    app.state.gate = ConcurrencyGate(settings.max_concurrent_asks)
    app.state.llm = (
        None  # built on first use, so a live config without a provider fails per request, not at import (D-15)
    )

    # The web app is on another origin in development; allow exactly that origin and nothing else.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[postprocess.normalise_origin(settings.public_origin)],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )
    settings.kit_dist_dir.mkdir(parents=True, exist_ok=True)
    mount_kit(app, settings.kit_dist_dir)

    @app.exception_handler(SynapseError)
    async def _synapse_error(_: Request, exc: SynapseError) -> JSONResponse:
        envelope = exc.to_envelope()
        return JSONResponse(envelope.model_dump(), status_code=HTTP_STATUS[envelope.code])

    @app.exception_handler(RequestValidationError)
    async def _bad_body(_: Request, exc: RequestValidationError) -> JSONResponse:
        issues = [
            FieldIssue(path=".".join(str(p) for p in e["loc"][1:]) or "(body)", message=str(e["msg"]))
            for e in exc.errors()
        ]
        envelope = ErrorEnvelope(
            code="validation_failed", message="The request is not valid.", issues=issues, retryable=False
        )
        return JSONResponse(envelope.model_dump(), status_code=HTTP_STATUS["validation_failed"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    def checked_question(body: AskRequest) -> str:
        question = body.question.strip()
        if not question:
            raise BadRequest("The question is empty.")
        if len(question) > MAX_QUESTION_CHARS:
            raise BadRequest(f"The question is longer than {MAX_QUESTION_CHARS} characters.")
        return question

    def llm_for(request: Request) -> LLMService:
        if request.app.state.llm is None:
            request.app.state.llm = build_llm_service(settings, request.app.state.ledger)
        return request.app.state.llm

    def admitted(request: Request, question: str = Depends(checked_question)) -> tuple[str, int]:
        """Rate limit per client address, then a slot among the questions in flight. Raises RateLimited (HTTP 429) before any work starts."""
        client = request.client.host if request.client else "unknown"
        if not request.app.state.rate.allow(client):
            raise RateLimited("Too many questions in a short time. Wait a minute and try again.")
        token = request.app.state.gate.acquire()
        if token is None:
            raise RateLimited("The server is making as many Environments as it can right now. Try again in a moment.")
        return question, token

    @app.post("/ask", response_class=EventSourceResponse)
    async def ask(request: Request, admission: tuple[str, int] = Depends(admitted)) -> AsyncIterator[StreamEvent]:
        """The Mark 3 pipeline (D-23) on whatever LLM service is configured: fakes by default, nothing paid without the owner's go."""
        question, token = admission
        try:
            async for event in _ask_events(request, question):
                yield event
        finally:
            request.app.state.gate.release(token)

    async def _ask_events(request: Request, question: str) -> AsyncIterator[StreamEvent]:
        try:
            llm = llm_for(request)
        except SynapseError as exc:  # live mode without a provider: a clean error event, not a broken stream
            yield StreamErrorEvent(type="error", error=envelope_from_exception(exc))
            yield DoneEvent(type="done")
            return
        deps = Deps(
            kit_dist=settings.kit_dist_dir,
            public_origin=settings.public_origin,
            store=request.app.state.store,
            llm=llm,
            trace_path=settings.data_dir / "traces.jsonl",
            interaction_seconds=settings.verify_interaction_seconds,
            evidence=evidence_for(settings),
        )
        async for event in run_pipeline(question, deps):
            yield event

    @app.get("/spend")
    async def spend(request: Request) -> dict:
        """This month's LLM spend against the cap (P7 cost dashboard). Single operator, no auth (D-11): not for the public internet."""
        return request.app.state.ledger.summary()

    # ── the library and its lifecycle (P5). Single operator, no auth (D-11): these must not be exposed until the deploy gate. ──────────────────────

    def current_kit_shas() -> dict[str, str | None]:
        return {v: kit_bundle_sha256(settings.kit_dist_dir, v) for v in built_versions(settings.kit_dist_dir)}

    @app.get("/library")
    async def library(request: Request) -> dict:
        return {"environments": request.app.state.store.library(current_kit_shas())}

    @app.get("/library/{env_id}")
    async def library_item(env_id: str, request: Request) -> JSONResponse:
        """One Environment through the delivery gate, exactly as /ask delivers it."""
        try:
            block = deliver(
                request.app.state.store,
                env_id,
                public_origin=settings.public_origin,
                kit_dist=settings.kit_dist_dir,
                evidence=evidence_for(settings),
            )
        except VerificationFailed as failure:
            envelope = ErrorEnvelope(
                code="verification_refused",
                message="This Environment is not available.",
                issues=[FieldIssue(path=f"{failure.stage}/{failure.rule}", message=failure.reason)],
                retryable=False,
            )
            return JSONResponse(envelope.model_dump(), status_code=HTTP_STATUS["verification_refused"])
        return JSONResponse(block.model_dump(mode="json"))

    @app.get("/library/{env_id}/export")
    async def library_export(env_id: str, request: Request) -> Response:
        """The offline single-file copy of one Environment (P7). Built from the block the gate delivers, with the Kit bytes it was verified against."""
        try:
            block = deliver(
                request.app.state.store,
                env_id,
                public_origin=settings.public_origin,
                kit_dist=settings.kit_dist_dir,
                evidence=evidence_for(settings),
            )
            page = standalone_page(block, (settings.kit_dist_dir / block.kitVersion / "core.js").read_bytes())
        except (VerificationFailed, ExportRefused, OSError):
            envelope = ErrorEnvelope(
                code="verification_refused", message="This Environment cannot be exported.", issues=[], retryable=False
            )
            return JSONResponse(envelope.model_dump(), status_code=HTTP_STATUS["verification_refused"])
        return Response(
            page,
            media_type="text/html; charset=utf-8",
            headers={
                "content-disposition": f'attachment; filename="synapse-{block.id}.html"',
                "cache-control": "no-store",
            },
        )

    def _known(request: Request, env_id: str) -> SqliteEnvironmentStore:
        store: SqliteEnvironmentStore = request.app.state.store
        if store.get_record(env_id) is None:
            raise NotFound(f"No verified Environment '{env_id}'.")
        return store

    @app.post("/library/{env_id}/flag")
    async def flag(env_id: str, body: _Note, request: Request) -> dict:
        """Anyone can say an Environment looks wrong. A flag is recorded and counted; it does not take the Environment down by itself."""
        return {"flags": _known(request, env_id).flag(env_id, body.note)}

    @app.post("/library/{env_id}/withdraw")
    async def withdraw(env_id: str, body: _Note, request: Request) -> dict:
        _known(request, env_id).withdraw(env_id, body.note)
        return {"status": "withdrawn"}

    @app.post("/library/{env_id}/restore")
    async def restore(env_id: str, request: Request) -> dict:
        _known(request, env_id).restore(env_id)
        return {"status": "active"}

    return app
