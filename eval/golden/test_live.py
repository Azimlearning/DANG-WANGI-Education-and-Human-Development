"""The paid-run script's guarantees, with no real provider: it refuses without a cap, sends nothing unless a person types an amount, stays inside it, and
records what it measured. The real `AnthropicProvider` is replaced by a spy that fails the test if anything tries to send."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from api.core.settings import Settings
from api.llm.factory import build_ledger
from api.llm.models import ANTHROPIC_MODELS
from api.llm.providers.fake import FakeProvider
from api.llm.service import LLMService
from api.pipeline import fakes
from eval.golden import live
from eval.golden.run import load

DUMMY_KEY = "test-key-not-real"


def write_env(tmp_path: Path, *, key: bool = True, cap: str | None = "5") -> Path:
    lines = [f"DATA_DIR={tmp_path / 'data'}", f"LEDGER_PATH={tmp_path / 'data' / 'ledger.db'}"]
    if key:
        lines.append(f"ANTHROPIC_API_KEY={DUMMY_KEY}")
    if cap is not None:
        lines.append(f"LLM_MONTHLY_CAP_USD={cap}")
    path = tmp_path / ".env"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class SendSpy:
    """Stands in for AnthropicProvider: building it is fine, sending is a failure."""

    name = "anthropic"
    sent = 0

    def __init__(self, key: str) -> None:
        assert key == DUMMY_KEY

    def model_for(self, tier):  # noqa: ANN001, ANN201
        return ANTHROPIC_MODELS[tier]

    async def complete(self, request, model):  # noqa: ANN001, ANN201
        SendSpy.sent += 1
        raise AssertionError("a request was sent")


@pytest.fixture(autouse=True)
def no_real_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    SendSpy.sent = 0
    monkeypatch.setattr("api.llm.factory.AnthropicProvider", SendSpy)
    for name in ("ANTHROPIC_API_KEY", "LLM_MONTHLY_CAP_USD", "SYNAPSE_LLM_MODE", "LEDGER_PATH", "DATA_DIR", "CORPUS_DIR"):
        monkeypatch.delenv(name, raising=False)


def questions(n: int = 1) -> list[dict]:
    return load("vertical")[:n]


def test_without_a_monthly_cap_nothing_is_sent_and_the_missing_setting_is_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = live.main_live(questions(), ask=lambda _p: "1", env_file=write_env(tmp_path, cap=None))
    out = capsys.readouterr().out
    assert code == 2 and "LLM_MONTHLY_CAP_USD" in out and SendSpy.sent == 0


def test_without_a_key_nothing_is_sent_and_the_missing_setting_is_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = live.main_live(questions(), ask=lambda _p: "1", env_file=write_env(tmp_path, key=False))
    assert code == 2 and "ANTHROPIC_API_KEY" in capsys.readouterr().out and SendSpy.sent == 0


@pytest.mark.parametrize("typed", ["", "no", "-1", "0", "abc", "nan", "inf", "99999"])
def test_anything_but_a_valid_amount_within_the_cap_sends_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str], typed: str) -> None:
    code = live.main_live(questions(), ask=lambda _p: typed, env_file=write_env(tmp_path))
    out = capsys.readouterr().out
    assert code == 1 and "Nothing was sent" in out and SendSpy.sent == 0
    assert "hard bound" in out and "remains" in out  # the person is shown what it could cost and what is left before being asked


def test_a_closed_input_is_not_approval(tmp_path: Path) -> None:
    def closed(_prompt: str) -> str:
        raise EOFError

    assert live.main_live(questions(), ask=closed, env_file=write_env(tmp_path)) == 1 and SendSpy.sent == 0


def test_a_run_whose_hard_bound_does_not_fit_the_cap_is_refused_before_asking(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    asked = []
    code = live.main_live(questions(), ask=lambda p: asked.append(p) or "1", env_file=write_env(tmp_path, cap="0.01"))
    assert code == 1 and asked == [] and "does not fit" in capsys.readouterr().out and SendSpy.sent == 0


def test_the_amount_is_parsed_the_way_a_person_types_it() -> None:
    assert live.parse_amount("0.75") == 0.75 and live.parse_amount(" $1 ") == 1.0
    assert all(live.parse_amount(x) is None for x in ("", "0", "-2", "x", "nan", "inf", "1,5"))
    assert live.confirmed_amount(lambda _p: "0.5", 1.0) == 0.5
    assert live.confirmed_amount(lambda _p: "2", 1.0) is None  # more than remains of the cap


def test_the_projection_orders_low_high_and_hard_bound_for_every_question() -> None:
    p = live.project(questions(3))
    assert len(p.per_question) == 3 and 0 < p.low < p.high < p.hard_bound
    assert all(0 < v["low"] < v["high"] < v["hard_bound"] for v in p.per_question.values())


def run(tmp_path: Path, approved: float, n: int = 1) -> dict:
    """The real pipeline and verifier on fakes that are priced like the provider, so the ledger books real-looking dollars."""
    settings = Settings(_env_file=write_env(tmp_path)).model_copy(update={"synapse_llm_mode": "live"})  # pyright: ignore[reportCallIssue]
    ledger = build_ledger(settings)
    llm = LLMService(FakeProvider(fakes.fake_responder, name="anthropic", models=ANTHROPIC_MODELS), None, ledger)
    qs = questions(n)
    try:
        return asyncio.run(
            live.run_live(
                settings, llm, ledger, qs, live.project(qs), approved, tmp_path / "store.db", out_dir=tmp_path / "results", interaction_seconds=1.0
            )
        )
    finally:
        ledger.close()


def test_an_approved_run_makes_the_environment_books_the_cost_and_writes_what_it_measured(tmp_path: Path) -> None:
    result = run(tmp_path, approved=5.0)
    (record,) = result["questions"]
    assert record["environment"] and record["lane"] and record["label"] == "model-checked"
    assert record["cost_usd"] > 0 and result["spent_usd"] == pytest.approx(record["cost_usd"], abs=1e-6)
    assert {c["purpose"] for c in record["calls"]} >= {"explain", "plan"} and all(c["status"] == "ok" for c in record["calls"])
    saved = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    assert saved["approved_usd"] == 5.0 and saved["questions"][0]["id"] == record["id"]


def test_it_stops_starting_questions_when_the_approved_amount_could_not_cover_the_next(tmp_path: Path) -> None:
    result = run(tmp_path, approved=0.0001, n=2)
    assert result["questions"] == [] and result["spent_usd"] == 0 and "stopped before" in result["stopped"]


def test_the_amount_typed_becomes_the_ceiling_of_the_run_ledger_and_each_run_gets_a_fresh_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not only a gate to start: the ledger the run uses is capped at what was spent plus the approved amount, so no call can pass it."""
    seen: dict = {}

    async def fake_run_live(settings, llm, ledger, qs, projection, approved, store_path, **kw):  # noqa: ANN001, ANN003, ANN202
        seen.update(remaining=ledger.remaining_usd(), approved=approved, store=store_path)
        return {"questions": [], "spent_usd": 0.0, "stopped": None, "path": "none"}

    monkeypatch.setattr(live, "run_live", fake_run_live)
    assert live.main_live(questions(), ask=lambda _p: "0.2", env_file=write_env(tmp_path)) == 0
    assert seen["approved"] == 0.2 and seen["remaining"] == pytest.approx(0.2)  # the monthly cap is $5; the run may use only $0.20 of it
    assert seen["store"].name.startswith("golden-live-") and not seen["store"].exists()  # never a store a previous run filled


def test_a_refusal_a_retry_cannot_fix_stops_the_run_instead_of_asking_the_rest_of_the_questions(tmp_path: Path) -> None:
    from api.llm.providers.base import ProviderFailure

    class Refuses:
        name = "anthropic"
        calls = 0

        def model_for(self, tier):  # noqa: ANN001, ANN201
            return ANTHROPIC_MODELS[tier]

        async def complete(self, request, model):  # noqa: ANN001, ANN201
            Refuses.calls += 1
            raise ProviderFailure("anthropic", "HTTP 401 authentication_error", "auth")

    settings = Settings(_env_file=write_env(tmp_path)).model_copy(update={"synapse_llm_mode": "live"})  # pyright: ignore[reportCallIssue]
    ledger = build_ledger(settings)
    llm = LLMService(Refuses(), None, ledger)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    qs = questions(3)
    try:
        result = asyncio.run(
            live.run_live(settings, llm, ledger, qs, live.project(qs), 5.0, tmp_path / "s.db", out_dir=tmp_path / "r", interaction_seconds=1.0)
        )
    finally:
        ledger.close()
    assert len(result["questions"]) == 1 and "retrying will not help" in result["stopped"]
    assert result["questions"][0]["errors"] == [{"code": "provider_unavailable", "retryable": False}]
    assert Refuses.calls <= 2  # the router fallback and the explainer of the first question, not three questions' worth
