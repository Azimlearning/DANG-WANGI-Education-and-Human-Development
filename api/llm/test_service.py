"""The seam's guarantees: fakes by default and offline, live mode needs a key and a cap, the cap refuses before any
provider call, and every call is written to the ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from api.core.errors import ProviderRejected, ProviderUnavailable, SpendCapExceeded
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
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "ledger.db"))
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


async def test_a_timeout_is_booked_at_its_input_cost_not_nothing(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    service = LLMService(
        FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="timed out", fail_kind="timeout"),
        None,
        ledger,
    )
    with pytest.raises(ProviderUnavailable):
        await service.complete(LLMRequest(prompt="x" * 3000, purpose="plan"))
    (row,) = ledger.rows()
    assert row["status"] == "failed" and row["cost_usd"] > 0


@pytest.mark.parametrize("kind", ["credit_exhausted", "auth", "bad_request"])
async def test_a_failure_a_retry_cannot_fix_stops_at_once_and_says_it_is_not_the_cap(tmp_path: Path, kind: str) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    first = FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="rejected", fail_kind=kind)  # type: ignore[arg-type]
    fallback = FakeProvider(name="fallbackco", models=ANTHROPIC_MODELS)
    service = LLMService(first, fallback, ledger)
    with pytest.raises(ProviderRejected) as err:
        await service.complete(LLMRequest(prompt="hi", purpose="plan"))
    assert "not the spend cap" in str(err.value) and err.value.retryable is False
    assert fallback.calls == []  # a balance or key problem is never retried on another provider


async def test_a_cancelled_call_is_booked_for_its_input_and_the_cancellation_propagates(tmp_path: Path) -> None:
    import asyncio

    class Hangs:
        name = "anthropic"

        def model_for(self, tier):  # noqa: ANN001, ANN201
            return ANTHROPIC_MODELS[tier]

        async def complete(self, request, model):  # noqa: ANN001, ANN201
            await asyncio.sleep(10)

    ledger = _ledger(tmp_path, cap=10.0)
    service = LLMService(Hangs(), None, ledger)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    task = asyncio.create_task(service.complete(LLMRequest(prompt="x" * 3000, purpose="plan")))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    (row,) = ledger.rows()
    assert row["cost_usd"] > 0 and ledger.remaining_usd() == pytest.approx(10.0 - row["cost_usd"])


async def test_a_run_whose_worst_case_does_not_fit_the_cap_is_refused_before_it_starts(tmp_path: Path) -> None:
    service = LLMService(FakeProvider(name="anthropic", models=ANTHROPIC_MODELS), None, _ledger(tmp_path, cap=0.50))
    service.ensure_budget(0.40)
    with pytest.raises(SpendCapExceeded):
        service.ensure_budget(0.80)
    assert (
        LLMService(FakeProvider(), None, _ledger(tmp_path / "u", cap=None)).ensure_budget(99.0) is None
    )  # no cap: nothing to check


@pytest.mark.usefixtures("clean_env")
def test_live_mode_is_never_built_uncapped_or_with_a_relative_ledger_even_without_load_settings(tmp_path: Path) -> None:
    from api.core.settings import Settings

    def settings(**kw: object) -> Settings:
        return Settings.model_validate({"synapse_llm_mode": "live", "anthropic_api_key": "sk-x", **kw})

    with pytest.raises(ConfigError) as err:
        build_ledger(settings(ledger_path=str(tmp_path / "l.db")))
    assert "LLM_MONTHLY_CAP_USD" in str(err.value)
    with pytest.raises(ConfigError) as err:
        build_ledger(settings(llm_monthly_cap_usd=1))
    assert "LEDGER_PATH" in str(err.value)


async def test_the_spend_summary_splits_by_purpose_and_model_and_counts_failed_calls(tmp_path: Path) -> None:
    ledger = SpendLedger(engine_for(tmp_path / "l.db"), 1.0)
    service = LLMService(FakeProvider(name="anthropic", models=ANTHROPIC_MODELS), None, ledger)
    await service.complete(LLMRequest(prompt="a" * 300, purpose="plan", tier="standard", max_tokens=100))
    await service.complete(LLMRequest(prompt="b" * 300, purpose="explain", tier="light", max_tokens=100))
    broken = LLMService(
        FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="x", fail_kind="transient"), None, ledger
    )
    with pytest.raises(Exception):  # noqa: B017, PT011
        await broken.complete(LLMRequest(prompt="c", purpose="plan", tier="standard", max_tokens=10))
    s = ledger.summary()
    assert s["cap_usd"] == 1.0 and s["calls"] == 3 and s["failed_calls"] == 1
    assert set(s["by_purpose"]) == {"plan", "explain"} and set(s["by_model"]) == {
        "claude-sonnet-5-5",
        "claude-haiku-5-5",
    }
    assert s["spent_usd"] == pytest.approx(sum(s["by_model"].values())) and s["remaining_usd"] == pytest.approx(
        1.0 - s["spent_usd"]
    )
