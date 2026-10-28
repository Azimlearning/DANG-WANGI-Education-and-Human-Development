"""Prompt caching (B6, D-55): off by default, priced correctly when on, and never able to under-count spend. Everything here uses a mock transport; nothing is billed."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from api.core.settings import load_settings
from api.llm.ledger import SpendLedger, engine_for
from api.llm.pricing import CACHE_WRITE_MULTIPLIER, cost_usd, estimate_call_cost
from api.llm.providers.anthropic import AnthropicProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest

SONNET = "claude-sonnet-5-5"  # $2 in, $10 out per million; a cache read is 5 percent of the input rate
HAIKU = "claude-haiku-5-5"  # $0.10 in; a cache read is 10 percent
MILLION = 1_000_000


def ledger(tmp_path: Path, cap: float | None = 5.0) -> SpendLedger:
    return SpendLedger(engine_for(tmp_path / "ledger.db"), cap, clock=lambda: datetime(2026, 10, 27, tzinfo=UTC))


# ── the arithmetic ──────────────────────────────────────────────────────────────


def test_with_no_cache_counts_the_price_is_the_plain_base_rate_price() -> None:
    assert cost_usd("anthropic", SONNET, MILLION, MILLION) == pytest.approx(2.0 + 10.0)
    assert cost_usd("anthropic", SONNET, MILLION, 0, 0, 0) == pytest.approx(2.0)


def test_a_cache_read_costs_a_fraction_and_a_cache_write_costs_more_than_base() -> None:
    assert cost_usd("anthropic", SONNET, MILLION, 0, cache_read_tokens=MILLION) == pytest.approx(2.0 * 0.05)
    assert cost_usd("anthropic", HAIKU, MILLION, 0, cache_read_tokens=MILLION) == pytest.approx(0.10 * 0.10)
    assert cost_usd("anthropic", SONNET, MILLION, 0, cache_write_tokens=MILLION) == pytest.approx(2.0 * CACHE_WRITE_MULTIPLIER)
    assert CACHE_WRITE_MULTIPLIER > 1.0  # a write may never be priced below the base rate


def test_plain_reads_and_writes_add_up() -> None:
    got = cost_usd("anthropic", SONNET, MILLION, 0, cache_read_tokens=600_000, cache_write_tokens=100_000)
    assert got == pytest.approx(0.3 * 2.0 + 0.6 * 2.0 * 0.05 + 0.1 * 2.0 * CACHE_WRITE_MULTIPLIER)


def test_counts_larger_than_the_input_cannot_make_a_call_cheaper_than_it_was() -> None:
    """A reply that reports more cached tokens than input tokens is clamped, so a malformed usage block cannot push the price to or below zero."""
    got = cost_usd("anthropic", SONNET, 1000, 0, cache_read_tokens=5000, cache_write_tokens=5000)
    assert got == pytest.approx(1000 * 2.0 * 0.05 / MILLION)
    assert cost_usd("anthropic", SONNET, 1000, 0, cache_read_tokens=-50) == pytest.approx(cost_usd("anthropic", SONNET, 1000, 0))


def test_a_model_the_table_does_not_know_gets_no_read_discount() -> None:
    unknown = cost_usd("anthropic", "claude-mystery", MILLION, 0, cache_read_tokens=MILLION)
    assert unknown == pytest.approx(4.0)  # priced as the dearest model, with the read counted at the full rate


def test_worst_case_prices_all_input_as_writes_and_a_free_provider_stays_free() -> None:
    assert cost_usd("anthropic", SONNET, MILLION, 0, assume_cache_writes=True) == pytest.approx(2.0 * CACHE_WRITE_MULTIPLIER)
    assert cost_usd("fake", SONNET, MILLION, MILLION, 500_000, 500_000, assume_cache_writes=True) == 0.0


def test_the_cap_reserves_more_for_a_call_that_asks_for_caching() -> None:
    plain = LLMRequest(prompt="x" * 300, purpose="plan", system="y" * 30_000)
    cached = LLMRequest(prompt="x" * 300, purpose="plan", system="y" * 30_000, cache_system=True)
    assert estimate_call_cost("anthropic", SONNET, cached) > estimate_call_cost("anthropic", SONNET, plain)  # a first call writes the cache


# ── the request and the reply ───────────────────────────────────────────────────


def reply(**usage: int) -> httpx.Response:
    body = {
        "id": "m",
        "type": "message",
        "role": "assistant",
        "model": SONNET,
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "output_tokens": 20, **usage},
    }
    return httpx.Response(200, json=body)


def provider(handler) -> AnthropicProvider:  # noqa: ANN001
    return AnthropicProvider("dummy-test-value", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_the_system_prompt_is_a_plain_string_unless_caching_was_asked_for() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return reply()

    p = provider(handler)
    await p.complete(LLMRequest(prompt="q", purpose="plan", system="Be brief."), SONNET)
    await p.complete(LLMRequest(prompt="q", purpose="plan", system="Be brief.", cache_system=True), SONNET)
    assert seen[0]["system"] == "Be brief."
    assert seen[1]["system"] == [{"type": "text", "text": "Be brief.", "cache_control": {"type": "ephemeral"}}]


async def test_the_replys_cache_usage_is_carried_and_input_count_stays_the_total() -> None:
    result = await provider(lambda r: reply(cache_creation_input_tokens=300, cache_read_input_tokens=700)).complete(
        LLMRequest(prompt="q", purpose="plan", system="s", cache_system=True), SONNET
    )
    assert (result.tokens_in, result.cache_write_tokens, result.cache_read_tokens) == (1100, 300, 700)


# ── the service and the ledger ──────────────────────────────────────────────────


async def test_with_caching_on_the_service_sends_the_marker_and_books_the_discounted_cost(tmp_path: Path) -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return reply(cache_read_input_tokens=900_000, input_tokens=100_000)

    book = ledger(tmp_path)
    service = LLMService(provider(handler), None, book, prompt_caching=True)
    result = await service.complete(LLMRequest(prompt="q", purpose="plan", system="Stable instructions."))
    assert isinstance(seen[0]["system"], list)
    # 100 000 plain + 900 000 read, 20 output: 0.1 M x $2 + 0.9 M x $2 x 5% + 20 x $10 per M
    assert result.cost_usd == pytest.approx(0.1 * 2.0 + 0.9 * 2.0 * 0.05 + 20 * 10.0 / MILLION)
    assert result.cache_read_tokens == 900_000
    (row,) = book.rows()
    assert (row["cache_read_tokens"], row["cache_write_tokens"]) == (900_000, 0)
    assert book.summary()["cache_read_tokens"] == 900_000
    assert book.month_total() == pytest.approx(result.cost_usd)


async def test_with_caching_off_nothing_changes(tmp_path: Path) -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return reply()

    service = LLMService(provider(handler), None, ledger(tmp_path))
    result = await service.complete(LLMRequest(prompt="q", purpose="plan", system="Stable instructions."))
    assert seen[0]["system"] == "Stable instructions."
    assert result.cost_usd == pytest.approx(cost_usd("anthropic", SONNET, 100, 20))
    assert (result.cache_read_tokens, result.cache_write_tokens) == (0, 0)


async def test_a_call_with_no_system_prompt_is_never_marked_for_caching(tmp_path: Path) -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return reply()

    service = LLMService(provider(handler), None, ledger(tmp_path), prompt_caching=True)
    await service.complete(LLMRequest(prompt="q", purpose="plan"))
    assert "system" not in seen[0]


async def test_a_cache_write_is_booked_above_the_base_rate_so_it_cannot_be_under_counted(tmp_path: Path) -> None:
    service = LLMService(
        provider(lambda r: reply(cache_creation_input_tokens=MILLION, input_tokens=0)), None, ledger(tmp_path, cap=50.0), prompt_caching=True
    )
    result = await service.complete(LLMRequest(prompt="q", purpose="plan", system="s", max_tokens=20))
    assert result.cost_usd == pytest.approx(2.0 * CACHE_WRITE_MULTIPLIER + 20 * 10.0 / MILLION)
    assert result.cost_usd > cost_usd("anthropic", SONNET, MILLION, 20)


def test_would_fit_counts_the_write_premium_when_caching_is_on(tmp_path: Path) -> None:
    request = LLMRequest(prompt="q" * 3000, purpose="plan", system="s" * 300_000, max_tokens=1000)
    plain = estimate_call_cost("anthropic", SONNET, request)
    cached = estimate_call_cost("anthropic", SONNET, LLMRequest(**{**request.__dict__, "cache_system": True}))
    book = ledger(tmp_path, cap=(plain + cached) / 2)  # room for the plain estimate but not the cached one
    assert LLMService(provider(lambda r: reply()), None, book).would_fit([request]) is True
    assert LLMService(provider(lambda r: reply()), None, book, prompt_caching=True).would_fit([request]) is False


# ── an existing ledger, and the setting ─────────────────────────────────────────


def test_a_ledger_written_before_the_cache_columns_keeps_its_rows_and_gains_the_columns(tmp_path: Path) -> None:
    path = tmp_path / "ledger.db"
    old = sqlite3.connect(path)
    old.execute(
        "CREATE TABLE spend_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, ts VARCHAR NOT NULL, month VARCHAR NOT NULL, provider VARCHAR NOT NULL, "
        "model VARCHAR NOT NULL, tokens_in INTEGER NOT NULL, tokens_out INTEGER NOT NULL, cost_usd FLOAT NOT NULL, purpose VARCHAR NOT NULL, status VARCHAR NOT NULL)"
    )
    old.execute(
        "INSERT INTO spend_ledger (ts, month, provider, model, tokens_in, tokens_out, cost_usd, purpose, status) "
        "VALUES ('t', '2026-10', 'anthropic', 'm', 1, 2, 0.26, 'plan', 'ok')"
    )
    old.commit()
    old.close()
    book = SpendLedger(engine_for(path), 5.0, clock=lambda: datetime(2026, 10, 27, tzinfo=UTC))
    assert book.month_total() == pytest.approx(0.26)  # the money already spent is still counted
    (row,) = book.rows()
    assert (row["cache_read_tokens"], row["cache_write_tokens"]) == (0, 0)
    SpendLedger(engine_for(path), 5.0)  # opening it again changes nothing and does not fail


@pytest.mark.usefixtures("clean_env")
def test_caching_is_off_unless_the_setting_turns_it_on(monkeypatch: pytest.MonkeyPatch) -> None:
    assert load_settings(env_file=None).prompt_caching is False
    monkeypatch.setenv("PROMPT_CACHING", "true")
    assert load_settings(env_file=None).prompt_caching is True
