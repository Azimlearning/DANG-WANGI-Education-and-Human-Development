"""The Anthropic provider against a mock transport: no socket is opened and nothing is billed."""

from __future__ import annotations

import json

import httpx
import pytest

from api.llm.models import ANTHROPIC_MODELS
from api.llm.pricing import PRICES_PER_MTOK
from api.llm.providers.anthropic import API_VERSION, AnthropicProvider, thinking_for
from api.llm.providers.base import ProviderFailure
from api.llm.types import LLMRequest

KEY = "sk-ant-test-0000000000000000"


def provider(handler, **kw) -> AnthropicProvider:  # noqa: ANN001
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AnthropicProvider(KEY, client=client, **kw)


def ok(text: str = "hello", stop: str = "end_turn", **usage: int) -> httpx.Response:
    body = {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop,
        "usage": {"input_tokens": 10, "output_tokens": 5, **usage},
    }
    return httpx.Response(200, json=body)


def err(status: int, error_type: str, message: str = "x", headers: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status, json={"type": "error", "error": {"type": error_type, "message": message}}, headers=headers or {}
    )


REQ = LLMRequest(prompt="Why does a spring stretch?", purpose="explain", system="Be brief.", max_tokens=200)


async def test_a_good_reply_carries_text_and_usage_and_the_request_has_the_documented_shape() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return ok("A spring stretches.", cache_read_input_tokens=7, cache_creation_input_tokens=3)

    result = await provider(handler).complete(REQ, "claude-sonnet-5-5")
    assert result.text == "A spring stretches." and (result.tokens_in, result.tokens_out) == (20, 5)
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["headers"]["x-api-key"] == KEY and seen["headers"]["anthropic-version"] == API_VERSION
    body = seen["body"]
    assert body["model"] == "claude-sonnet-5-5" and body["max_tokens"] == 200 and body["system"] == "Be brief."
    assert body["messages"] == [{"role": "user", "content": "Why does a spring stretch?"}]
    assert body["thinking"] == {"type": "between_tools"} and "output_config" not in body


def test_thinking_is_set_per_model_and_never_disabled_where_the_model_refuses_it() -> None:
    assert thinking_for("claude-sonnet-5-5") == {"type": "between_tools"}
    assert thinking_for("claude-haiku-5-5") == {"type": "disabled"}
    assert thinking_for("claude-opus-5-5") is None  # always thinks; the field is omitted


async def test_effort_is_sent_only_where_the_model_thinks() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return ok()

    p = provider(handler)
    request = LLMRequest(prompt="x", purpose="plan", effort="xhigh", max_tokens=100)
    await p.complete(request, "claude-sonnet-5-5")
    await p.complete(request, "claude-opus-5-5")
    assert "output_config" not in bodies[0] and bodies[1]["output_config"] == {"effort": "xhigh"}


async def test_only_text_blocks_are_returned_and_a_thinking_block_is_ignored() -> None:
    def handler(_r: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [{"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "answer"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 2},
            },
        )

    assert (await provider(handler).complete(REQ, "claude-opus-5-5")).text == "answer"


@pytest.mark.parametrize(
    ("response", "kind"),
    [
        (err(400, "invalid_request_error", "Your credit balance is too low to access the API"), "credit_exhausted"),
        (err(400, "invalid_request_error", "You have reached your workspace spend limit"), "credit_exhausted"),
        (err(400, "invalid_request_error", "messages.0: bad"), "bad_request"),
        (err(401, "authentication_error"), "auth"),
        (err(402, "billing_error"), "credit_exhausted"),
        (err(403, "permission_error"), "auth"),
        (err(404, "not_found_error"), "bad_request"),
        (err(413, "request_too_large"), "bad_request"),
        (err(429, "rate_limit_error", headers={"retry-after": "5"}), "transient"),
        (err(429, "rate_limit_error"), "credit_exhausted"),  # no retry-after: the tier spend cap
        (err(500, "api_error"), "transient"),
        (err(504, "timeout_error"), "timeout"),
        (err(529, "overloaded_error"), "transient"),
    ],
)
async def test_http_errors_map_to_the_failure_kinds_the_service_acts_on(response: httpx.Response, kind: str) -> None:
    with pytest.raises(ProviderFailure) as raised:
        await provider(lambda _r: response).complete(REQ, "claude-sonnet-5-5")
    assert raised.value.kind == kind


async def test_a_reply_cut_off_at_max_tokens_is_a_truncation_failure() -> None:
    with pytest.raises(ProviderFailure) as raised:
        await provider(lambda _r: ok("partial", stop="max_tokens")).complete(REQ, "claude-sonnet-5-5")
    assert raised.value.kind == "truncated"


async def test_an_empty_or_malformed_reply_is_a_transient_failure() -> None:
    for response in (
        httpx.Response(
            200, json={"content": [], "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1}}
        ),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"nope": 1}),
    ):
        with pytest.raises(ProviderFailure) as raised:
            await provider(lambda _r, resp=response: resp).complete(REQ, "claude-sonnet-5-5")  # type: ignore[misc]
        assert raised.value.kind == "transient"


async def test_timeouts_and_network_errors_are_classified() -> None:
    def slow(_r: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    def down(_r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(ProviderFailure) as raised:
        await provider(slow).complete(REQ, "claude-sonnet-5-5")
    assert raised.value.kind == "timeout"
    with pytest.raises(ProviderFailure) as raised:
        await provider(down).complete(REQ, "claude-sonnet-5-5")
    assert raised.value.kind == "transient"


async def test_no_error_carries_the_key_the_prompt_or_the_response_message() -> None:
    secret_message = "Your prompt said: Why does a spring stretch? and key " + KEY
    with pytest.raises(ProviderFailure) as raised:
        await provider(lambda _r: err(400, "invalid_request_error", secret_message)).complete(REQ, "claude-sonnet-5-5")
    text = str(raised.value) + raised.value.reason
    assert KEY not in text and "spring" not in text and "HTTP 400 invalid_request_error" in text


def test_an_empty_key_is_refused_and_every_tier_model_has_a_price() -> None:
    with pytest.raises(ValueError):
        AnthropicProvider("")
    assert set(ANTHROPIC_MODELS.values()) <= set(PRICES_PER_MTOK)
