"""The seam's guarantees: fakes by default and offline, live mode needs a key and a cap, the cap refuses before any
provider call, and every call is written to the ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from api.core.errors import ProviderUnavailable, SpendCapExceeded
from api.core.settings import ConfigError, load_settings
from api.llm.factory import build_ledger, build_llm_service
from api.llm.ledger import SpendLedger, engine_for
from api.llm.models import ANTHROPIC_MODELS
from api.llm.providers.fake import FakeProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest


def _ledger(tmp_path: Path, cap: float | None) -> SpendLedger:
    return SpendLedger(engine_for(tmp_path / "ledger.db"), cap, clock=lambda: datetime(2026, 10, 16, tzinfo=UTC))


@pytest.mark.usefixtures("clean_env", "no_network")
async def test_default_mode_is_fake_and_makes_no_network_call(tmp_path: Path) -> None:
    settings = load_settings(env_file=None)
    assert settings.synapse_llm_mode == "fake"
    settings = settings.model_copy(update={"data_dir": tmp_path})
    service = build_llm_service(settings, build_ledger(settings))
    result = await service.complete(LLMRequest(prompt="why does a spring stretch", purpose="explain"))
    assert result.provider == "fake"
    assert result.cost_usd == 0.0
    assert result.text.startswith("[fake:explain:")


@pytest.mark.usefixtures("clean_env")
async def test_fake_reply_is_deterministic(tmp_path: Path) -> None:
    provider = FakeProvider()
    service = LLMService(provider, None, _ledger(tmp_path, None))
    a = await service.complete(LLMRequest(prompt="same", purpose="explain"))
    b = await service.complete(LLMRequest(prompt="same", purpose="explain"))
    c = await service.complete(LLMRequest(prompt="different", purpose="explain"))
    assert a.text == b.text
    assert a.text != c.text


@pytest.mark.usefixtures("clean_env")
def test_live_mode_without_key_names_anthropic_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "5")
    with pytest.raises(ConfigError) as err:
        load_settings(env_file=None)
    assert "ANTHROPIC_API_KEY" in str(err.value)
    assert "LLM_MONTHLY_CAP_USD" not in str(err.value)


@pytest.mark.usefixtures("clean_env")
def test_live_mode_without_cap_names_llm_monthly_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    with pytest.raises(ConfigError) as err:
        load_settings(env_file=None)
    assert "LLM_MONTHLY_CAP_USD" in str(err.value)
    assert "ANTHROPIC_API_KEY" not in str(err.value)


@pytest.mark.usefixtures("clean_env")
def test_live_mode_rejects_a_zero_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "0")
    with pytest.raises(ConfigError, match="LLM_MONTHLY_CAP_USD"):
        load_settings(env_file=None)


@pytest.mark.usefixtures("clean_env")
def test_live_mode_builds_no_provider_in_p0(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "5")
    settings = load_settings(env_file=None).model_copy(update={"data_dir": tmp_path})
    with pytest.raises(ProviderUnavailable):
        build_llm_service(settings, build_ledger(settings))


async def test_request_over_the_cap_is_refused_before_the_provider(tmp_path: Path) -> None:
    # A fake that prices like a real provider: sonnet is $2 in, $10 out per million, so 16k output tokens is $0.16.
    spy = FakeProvider(name="anthropic", models=ANTHROPIC_MODELS)
    service = LLMService(spy, None, _ledger(tmp_path, cap=0.01))
    with pytest.raises(SpendCapExceeded):
        await service.complete(LLMRequest(prompt="x" * 300, purpose="plan", max_tokens=16_000))
    assert spy.calls == []


async def test_spend_accumulates_toward_the_cap(tmp_path: Path) -> None:
    # Each reply is 5000 characters (1250 output tokens), so each settled call really books about $0.0125.
    spy = FakeProvider(lambda _request: "y" * 5000, name="anthropic", models=ANTHROPIC_MODELS)
    ledger = _ledger(tmp_path, cap=0.05)
    service = LLMService(spy, None, ledger)
    request = LLMRequest(prompt="x" * 30, purpose="plan", max_tokens=2_000)  # worst case about $0.02
    await service.complete(request)
    await service.complete(request)
    assert ledger.month_total() == pytest.approx(0.025, abs=0.001)
    # Alone, 3000 output tokens ($0.03) fits under the cap; on top of the $0.025 already spent it does not.
    with pytest.raises(SpendCapExceeded):
        await service.complete(LLMRequest(prompt="x" * 30, purpose="plan", max_tokens=3_000))
    assert len(spy.calls) == 2


async def test_a_ledger_row_records_purpose_tokens_and_cost(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    service = LLMService(FakeProvider(name="anthropic", models=ANTHROPIC_MODELS), None, ledger)
    result = await service.complete(LLMRequest(prompt="hello there", purpose="explain", max_tokens=200))
    (row,) = ledger.rows()
    assert row["purpose"] == "explain"
    assert row["status"] == "ok"
    assert row["tokens_in"] == result.tokens_in > 0
    assert row["tokens_out"] == result.tokens_out > 0
    assert row["cost_usd"] == pytest.approx(result.cost_usd)
    assert row["cost_usd"] > 0


async def test_failed_attempt_is_recorded_as_failed_and_costs_nothing(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    broken = FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="timeout")
    service = LLMService(broken, None, ledger)
    with pytest.raises(ProviderUnavailable):
        await service.complete(LLMRequest(prompt="hi", purpose="explain"))
    (row,) = ledger.rows()
    assert row["status"] == "failed"
    assert row["cost_usd"] == 0.0
