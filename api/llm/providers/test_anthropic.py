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


async def test_a_reply_cut_off_at_max_tokens_is_a_truncation_failure_that_carries_its_usage() -> None:
    with pytest.raises(ProviderFailure) as raised:
        await provider(lambda _r: ok("partial", stop="max_tokens", output_tokens=200)).complete(
            REQ, "claude-sonnet-5-5"
        )
    assert raised.value.kind == "truncated"
    assert (raised.value.tokens_in, raised.value.tokens_out) == (10, 200)  # billed, so the ledger must see it


async def test_a_refusal_is_a_failure_that_carries_its_usage_and_never_returns_text() -> None:
    with pytest.raises(ProviderFailure) as raised:
        await provider(lambda _r: ok("I can't help with that.", stop="refusal")).complete(REQ, "claude-sonnet-5-5")
    assert raised.value.kind == "transient" and "refusal" in raised.value.reason
    assert (raised.value.tokens_in, raised.value.tokens_out) == (10, 5)


async def test_a_truncated_reply_is_booked_at_its_output_tokens_through_the_real_service_and_ledger(tmp_path) -> None:  # noqa: ANN001
    from datetime import UTC, datetime

    from api.core.errors import ProviderUnavailable
    from api.llm.ledger import SpendLedger, engine_for
    from api.llm.service import LLMService

    ledger = SpendLedger(engine_for(tmp_path / "l.db"), 10.0, clock=lambda: datetime(2026, 10, 18, tzinfo=UTC))
    p = provider(lambda _r: ok("partial", stop="max_tokens", input_tokens=500, output_tokens=4_000))
    with pytest.raises(ProviderUnavailable):
        await LLMService(p, None, ledger).complete(
            LLMRequest(prompt="Why?", purpose="plan", tier="standard", max_tokens=4_000)
        )
    # Sonnet 5.5 at $2 in and $10 out per million: 500 in and 4000 out is $0.041, not the input-only $0.001.
    assert ledger.month_total() == pytest.approx((500 * 2 + 4_000 * 10) / 1_000_000)


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
    # An empty reply that did report usage was billed: its tokens travel with the failure. One with no readable usage carries none.
    with pytest.raises(ProviderFailure) as billed:
        await provider(
            lambda _r: httpx.Response(
                200, json={"content": [], "stop_reason": "end_turn", "usage": {"input_tokens": 7, "output_tokens": 9}}
            )
        ).complete(REQ, "claude-sonnet-5-5")
    assert (billed.value.tokens_in, billed.value.tokens_out) == (7, 9)
    with pytest.raises(ProviderFailure) as unread:
        await provider(lambda _r: httpx.Response(200, text="not json")).complete(REQ, "claude-sonnet-5-5")
    assert unread.value.tokens_in is None and unread.value.tokens_out is None


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


def _sse(events: list[dict]) -> httpx.Response:
    lines = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)
    return httpx.Response(200, content=lines.encode("utf-8"), headers={"content-type": "text/event-stream"})


def _stream_events(text_parts: list[str], stop: str = "end_turn") -> list[dict]:
    return [
        {"type": "message_start", "message": {"model": "claude-sonnet-5-5", "usage": {"input_tokens": 120, "output_tokens": 1}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        *[{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": p}} for p in text_parts],
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": stop}, "usage": {"output_tokens": 42}},
        {"type": "message_stop"},
    ]


async def test_a_watched_call_streams_its_text_and_returns_the_same_response_with_its_usage() -> None:
    sent: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        sent.append(json.loads(req.content))
        return _sse(_stream_events(["<!doctype html>", "<p>hi", "</p>"]))

    seen: list[str] = []
    resp = await provider(handler).complete(LLMRequest(prompt="q", purpose="free"), "claude-sonnet-5-5", on_text=seen.append)
    assert sent[0]["stream"] is True
    assert seen == ["<!doctype html>", "<p>hi", "</p>"]
    assert resp.text == "<!doctype html><p>hi</p>"
    assert (resp.tokens_in, resp.tokens_out) == (120, 42)


async def test_a_watched_call_cut_off_or_errored_fails_as_an_unwatched_one_would() -> None:
    cut = provider(lambda req: _sse(_stream_events(["<p>half"], stop="max_tokens")))
    with pytest.raises(ProviderFailure) as info:
        await cut.complete(LLMRequest(prompt="q", purpose="free"), "claude-sonnet-5-5", on_text=lambda _t: None)
    assert info.value.kind == "truncated" and info.value.tokens_out == 42
    broken = provider(lambda req: _sse([{"type": "message_start", "message": {"usage": {"input_tokens": 5}}}, {"type": "error", "error": {"type": "overloaded_error", "message": "x"}}]))
    with pytest.raises(ProviderFailure) as info2:
        await broken.complete(LLMRequest(prompt="q", purpose="free"), "claude-sonnet-5-5", on_text=lambda _t: None)
    assert info2.value.kind == "transient"
    refused = provider(lambda req: httpx.Response(401, json={"type": "error", "error": {"type": "authentication_error", "message": "no"}}))
    with pytest.raises(ProviderFailure) as info3:
        await refused.complete(LLMRequest(prompt="q", purpose="free"), "claude-sonnet-5-5", on_text=lambda _t: None)
    assert info3.value.kind == "auth"
