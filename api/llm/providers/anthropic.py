"""The Anthropic Messages API provider (live mode). Read against the current docs on 2026-10-16 and re-read on 2026-10-18:
https://platform.claude.com/docs/en/api/messages, /api/errors and /build-with-claude/working-with-messages. Confirmed on the 18th: a
success body has `content[]` blocks (`text`, plus `thinking` that we ignore), `stop_reason` (`end_turn`, `max_tokens`, `refusal`, ...) and
`usage.input_tokens` / `usage.output_tokens`; an error body is `{"type": "error", "error": {"type", "message"}, "request_id"}`; Opus 5.5
rejects `thinking: disabled`, Sonnet 5.5 takes `between_tools`, Haiku 5.5 takes `disabled`.

Plain httpx, no SDK: the call is one POST, which keeps the dependency list short and lets the tests stand a mock transport in place of the
network. The provider does NOT retry (the service decides about fallback and the ledger books every attempt) and it never puts a key, a prompt or a
response body into an error: only the HTTP status, the API's error `type` and the request id.

Thinking: Sonnet 5.5 takes `{"type": "between_tools"}` (no up-front thinking), Haiku 5.5 takes `{"type": "disabled"}`; Opus 5.5 always thinks and bills
those tokens as output, so a caller using the heavy tier must leave room in `max_tokens`. Prompt caching is deliberately NOT used yet: the ledger prices
every input token at the base rate and cache writes cost more, so enabling it would under-count spend. Revisit with a measured saving.
"""

from __future__ import annotations

import httpx

from api.llm.models import ANTHROPIC_MODELS
from api.llm.providers.base import FailureKind, ProviderFailure
from api.llm.types import LLMRequest, ProviderResponse, Tier

API_VERSION = "2023-06-01"
BASE_URL = "https://api.anthropic.com"


def thinking_for(model: str) -> dict | None:
    """The `thinking` field to send for `model`, or None to omit it (the model's own default)."""
    if model.startswith("claude-sonnet-5"):
        return {"type": "between_tools"}
    if model.startswith("claude-haiku-5"):
        return {"type": "disabled"}
    return None


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        *,
        models: dict[Tier, str] | None = None,
        base_url: str = BASE_URL,
        timeout_seconds: float = 90.0,
        client: httpx.AsyncClient | None = None,
    ):
        if not api_key:
            raise ValueError("an API key is required")
        self._key = api_key
        self._models = models or ANTHROPIC_MODELS
        self._url = base_url.rstrip("/") + "/v1/messages"
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)

    def model_for(self, tier: Tier) -> str:
        return self._models[tier]

    def _body(self, request: LLMRequest, model: str) -> dict:
        body: dict = {
            "model": model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system:
            body["system"] = request.system
        thinking = thinking_for(model)
        if thinking is not None:
            body["thinking"] = thinking
        # `effort` is refused above "high" when thinking is off, so it is sent only for a model that thinks.
        if request.effort is not None and (thinking is None or thinking["type"] == "adaptive"):
            body["output_config"] = {"effort": request.effort}
        return body

    async def complete(self, request: LLMRequest, model: str) -> ProviderResponse:
        headers = {"x-api-key": self._key, "anthropic-version": API_VERSION, "content-type": "application/json"}
        try:
            reply = await self._client.post(self._url, headers=headers, json=self._body(request, model))
        except httpx.TimeoutException as exc:
            raise ProviderFailure(self.name, "the request timed out", "timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderFailure(self.name, f"network error ({type(exc).__name__})", "transient") from exc
        if reply.status_code != 200:
            raise self._failure(reply)
        try:
            data = reply.json()
            blocks = data["content"]
            text = "".join(str(b.get("text", "")) for b in blocks if b.get("type") == "text")
            usage = data["usage"]
            tokens_in = (
                int(usage["input_tokens"])
                + int(usage.get("cache_creation_input_tokens") or 0)
                + int(usage.get("cache_read_input_tokens") or 0)
            )
            tokens_out = int(usage["output_tokens"])
            stop = data.get("stop_reason")
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ProviderFailure(self.name, "the reply was not a Messages API response", "transient") from exc
        # From here the reply was real and billed, thinking tokens included, so every rejection below carries its usage for the ledger.
        billed = {"tokens_in": tokens_in, "tokens_out": tokens_out}
        if stop == "max_tokens":
            raise ProviderFailure(self.name, "the reply was cut off at max_tokens", "truncated", **billed)
        if stop == "refusal":
            raise ProviderFailure(self.name, "the model declined to answer (stop_reason refusal)", "transient", **billed)
        if not text.strip():
            raise ProviderFailure(self.name, f"the reply had no text (stop_reason {stop})", "transient", **billed)
        return ProviderResponse(
            text=text, model=str(data.get("model") or model), tokens_in=tokens_in, tokens_out=tokens_out
        )

    def _failure(self, reply: httpx.Response) -> ProviderFailure:
        """Map an HTTP error to a ProviderFailure. Only the status, the API's error type and the request id are kept."""
        status = reply.status_code
        try:
            error_type = str(reply.json()["error"]["type"])[:60]
        except (ValueError, KeyError, TypeError):
            error_type = "unknown"
        rid = reply.headers.get("request-id", "")[:40]
        reason = f"HTTP {status} {error_type}" + (f" ({rid})" if rid else "")
        kind: FailureKind
        if status == 402:
            kind = "credit_exhausted"  # billing_error
        elif status in (401, 403):
            kind = "auth"
        elif status == 429:
            # A rate limit carries retry-after; the monthly tier spend cap does not and keeps failing, so stop the run.
            kind = "transient" if reply.headers.get("retry-after") else "credit_exhausted"
        elif status == 400 and _is_spend_or_credit(reply):
            kind = "credit_exhausted"  # a workspace spend limit or a low credit balance also arrives as 400
        elif status == 504:
            kind = "timeout"
        elif status >= 500:
            kind = "transient"  # 500 api_error, 529 overloaded_error
        else:
            kind = "bad_request"  # 400, 404, 409, 413
        return ProviderFailure(self.name, reason, kind)


def _is_spend_or_credit(reply: httpx.Response) -> bool:
    try:
        message = str(reply.json()["error"]["message"]).lower()
    except (ValueError, KeyError, TypeError):
        return False
    return "credit balance" in message or "spend limit" in message or "usage limit" in message
