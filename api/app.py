"""The FastAPI application factory. Fakes by default: with SYNAPSE_LLM_MODE=fake nothing here touches the network."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse

from api import postprocess
from api.core.errors import HTTP_STATUS, BadRequest, NotFound, SynapseError, envelope_from_exception
from api.core.settings import Settings, load_settings
from api.kit import latest_version
from api.llm.factory import build_ledger, build_llm_service
from api.llm.service import LLMService
from api.llm.types import LLMRequest
from api.schema.generated import (
    AskRequest,
    DoneEvent,
    EnvironmentEvent,
    ErrorEnvelope,
    FieldIssue,
    MetaEvent,
    StreamErrorEvent,
    StreamEvent,
    TextDeltaEvent,
)
from api.seed import REFERENCE_SLUG, store_path
from api.sse import split_text
from api.static import mount_kit
from api.verify.gate import deliver
from api.verify.mint import VerificationFailed
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
        """P0: every question gets the reference Environment, delivered through the gate. There is no planner yet (P3)."""
        store: SqliteEnvironmentStore = request.app.state.store
        yield MetaEvent(
            type="meta",
            requestId=uuid.uuid4().hex,
            lane="instantiate",
            label="model-checked",
            kitVersion=latest_version(settings.kit_dist_dir),
        )
        try:
            reply = await llm_for(request).complete(
                LLMRequest(prompt=question, purpose="explain", tier="light", max_tokens=300)
            )
            for chunk in split_text(reply.text):
                yield TextDeltaEvent(type="text_delta", text=chunk)

            env_id = store.latest_id(REFERENCE_SLUG)
            if env_id is None:
                raise NotFound("No reference Environment is stored. Run `uv run python -m api.seed` first.")
            block = deliver(store, env_id, public_origin=settings.public_origin, kit_dist=settings.kit_dist_dir)
            yield EnvironmentEvent(type="environment", block=block)
        except VerificationFailed as failure:
            log.warning("delivery refused stage=%s rule=%s", failure.stage, failure.rule)
            yield StreamErrorEvent(
                type="error",
                error=ErrorEnvelope(
                    code="verification_refused",
                    message="This Environment failed a check and was not delivered.",
                    issues=[FieldIssue(path=f"{failure.stage}/{failure.rule}", message=failure.reason)],
                    retryable=False,
                ),
            )
        except Exception as exc:
            if not isinstance(exc, SynapseError):
                log.exception("unexpected failure in /ask")
            yield StreamErrorEvent(type="error", error=envelope_from_exception(exc))
        yield DoneEvent(type="done")

    return app
