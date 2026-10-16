"""The FastAPI application factory. Fakes by default: with SYNAPSE_LLM_MODE=fake nothing here touches the network."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse

from api import postprocess
from api.core.errors import HTTP_STATUS, BadRequest, SynapseError, envelope_from_exception
from api.core.settings import Settings, load_settings
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
from api.seed import store_path
from api.static import mount_kit
from api.verify.store import SqliteEnvironmentStore

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Synapse v4 API", version="0.1.0")
    app.state.settings = settings
    app.state.store = SqliteEnvironmentStore(store_path(settings))
    app.state.ledger = build_ledger(settings)
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

    @app.post("/ask", response_class=EventSourceResponse)
    async def ask(request: Request, question: str = Depends(checked_question)) -> AsyncIterator[StreamEvent]:
        """The Mark 3 pipeline (D-23) on whatever LLM service is configured: fakes by default, nothing paid without the owner's go."""
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
        )
        async for event in run_pipeline(question, deps):
            yield event

    return app
