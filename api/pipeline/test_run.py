"""The orchestrator under injected failures: every rung of the degrade ladder, the budget, the retry with named issues, slot fills, the gate, and
the trace. All on fakes; nothing here can spend money or open a socket."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from api.core.settings import Settings
from api.llm.factory import build_ledger
from api.llm.providers.fake import FakeProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest
from api.pipeline import fakes, run
from api.pipeline.run import Deps
from api.verify.mint import VerificationFailed
from api.verify.store import SqliteEnvironmentStore

SPRING = "Why does a spring stretch when I hang a weight on it?"
REPO = Path(__file__).resolve().parents[2]
GOLDEN_SPRING = json.loads((REPO / "data/plans/physics-f5-hookes_amali.json").read_text())
GOLDEN_OHM = json.loads((REPO / "data/plans/physics-f5-ohm_explorer.json").read_text())


def deps_for(tmp_path: Path, kit_dist: Path, responder, **extra) -> tuple[Deps, FakeProvider]:  # noqa: ANN001
    settings = Settings(_env_file=None, data_dir=tmp_path / "data", kit_dist_dir=kit_dist)  # type: ignore[call-arg]
    provider = FakeProvider(responder)
    llm = LLMService(provider, None, build_ledger(settings))
    deps = Deps(
        kit_dist=kit_dist,
        public_origin="http://localhost:3000",
        store=SqliteEnvironmentStore(tmp_path / "envs.db"),
        llm=llm,
        trace_path=tmp_path / "traces.jsonl",
        interaction_seconds=1.0,
        **extra,
    )
    return deps, provider


def collect(question: str, deps: Deps) -> list:
    async def go() -> list:
        return [e async for e in run.run(question, deps)]

    return asyncio.run(go())


def kinds(events: list) -> list[str]:
    return [e.type for e in events]


def degraded(events: list) -> list:
    return [e for e in events if e.type == "stage" and e.status == "degraded"]


def trace_records(deps: Deps) -> list[dict]:
    assert deps.trace_path is not None
    return json.loads(deps.trace_path.read_text().splitlines()[-1])["records"]


def test_the_happy_path_makes_three_model_calls_at_most_and_traces_every_layer(tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    events = collect(SPRING, deps)
    assert kinds(events)[0] == "meta" and kinds(events)[-2:] == ["environment", "done"]
    assert len(provider.calls) <= 3 and {c.purpose for c in provider.calls} >= {"explain", "plan"}
    layers = {r["layer"] for r in trace_records(deps)}
    assert {
        "intake",
        "route",
        "lookup",
        "explain",
        "llm:explain",
        "llm:plan",
        "plan_checks",
        "assemble",
        "verify",
        "deliver",
    } <= layers
    last = json.loads(deps.trace_path.read_text().splitlines()[-1])  # type: ignore[union-attr]
    assert last["outcome"] == "instantiate" and last["llm_calls"] == len(provider.calls)


def test_the_stream_order_is_stable_across_runs(tmp_path: Path, kit_dist: Path) -> None:
    a = kinds(collect(SPRING, deps_for(tmp_path / "a", kit_dist, fakes.fake_responder)[0]))
    b = kinds(collect(SPRING, deps_for(tmp_path / "b", kit_dist, fakes.fake_responder)[0]))
    assert a == b


def test_a_plan_the_planner_gets_wrong_twice_degrades_to_the_written_answer(tmp_path: Path, kit_dist: Path) -> None:
    def responder(request: LLMRequest) -> str:
        return "{}" if request.purpose == "plan" else fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and "plan" not in kinds(events)
    assert degraded(events) and sum(c.purpose == "plan" for c in provider.calls) == 2
    assert json.loads(deps.trace_path.read_text().splitlines()[-1])["outcome"] == "text_only"  # type: ignore[union-attr]
    assert any(e.type == "text_delta" for e in events)  # the words were already streamed


def test_a_bad_plan_is_retried_once_with_the_named_issue_and_then_accepted(tmp_path: Path, kit_dist: Path) -> None:
    bad = json.loads(json.dumps(GOLDEN_SPRING))
    bad["models"][0]["params"]["k"] = 0
    attempts: list[str] = []

    def responder(request: LLMRequest) -> str:
        if request.purpose == "plan":
            attempts.append(request.prompt)
            return json.dumps(bad if len(attempts) == 1 else GOLDEN_SPRING)
        return fakes.fake_responder(request)

    deps, _ = deps_for(tmp_path, kit_dist, responder)
    events = collect(SPRING, deps)
    assert kinds(events)[-2:] == ["environment", "done"]
    assert len(attempts) == 2 and "PLAN-003" in attempts[1] and "PLAN-003" not in attempts[0]


def test_a_start_outside_its_range_is_repaired_without_asking_the_model_again(tmp_path: Path, kit_dist: Path) -> None:
    bad = json.loads(json.dumps(GOLDEN_SPRING))
    bad["controls"][0]["value"] = 99

    def responder(request: LLMRequest) -> str:
        return json.dumps(bad) if request.purpose == "plan" else fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder)
    events = collect(SPRING, deps)
    assert kinds(events)[-2:] == ["environment", "done"] and sum(c.purpose == "plan" for c in provider.calls) == 1


def test_a_budget_overrun_degrades_instead_of_starting_another_call(
    tmp_path: Path, kit_dist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "MAX_LLM_CALLS", 2)  # explain, then one plan attempt

    def responder(request: LLMRequest) -> str:
        return "{}" if request.purpose == "plan" else fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder)
    events = collect(SPRING, deps)
    assert len(provider.calls) <= 2 and degraded(events)
    assert "allowed" in degraded(events)[0].note


def test_a_refusal_by_the_verifier_degrades_with_the_registered_student_message(tmp_path: Path, kit_dist: Path) -> None:
    def refuse(**_kw: object):  # noqa: ANN202
        raise VerificationFailed("render", "dead_control", "control 'load' changed no readout")

    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder, verify_fn=refuse)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and degraded(events)
    verify = next(r for r in trace_records(deps) if r["layer"] == "verify")
    assert verify["status"] == "refused" and verify["detail"]["code"] == "L2-004"


def test_a_row_the_gate_refuses_never_reaches_the_client(tmp_path: Path, kit_dist: Path) -> None:
    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    original = deps.store.put_verified

    def tamper(env):  # noqa: ANN001, ANN202
        original(env)
        with sqlite3.connect(tmp_path / "envs.db") as conn:
            conn.execute("UPDATE environments SET html = replace(html, 'Extension', 'Extensioz')")

    deps.store.put_verified = tamper  # type: ignore[method-assign]
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and degraded(events)


def _with_custom(plan: dict) -> dict:
    d = json.loads(json.dumps(plan))
    d["custom"] = [{"name": "extra", "purpose": "One more sentence."}]
    return d


def test_a_custom_slot_with_a_valid_fill_gives_the_compose_lane(tmp_path: Path, kit_dist: Path) -> None:
    def responder(request: LLMRequest) -> str:
        return json.dumps(_with_custom(GOLDEN_OHM)) if request.purpose == "plan" else fakes.fake_responder(request)

    deps, _ = deps_for(tmp_path, kit_dist, responder)
    events = collect("What happens to the current if I raise the resistance in a circuit?", deps)
    block = next(e for e in events if e.type == "environment").block
    assert block.lane == "compose" and block.label == "model-checked"
    assert "Try moving each slider" in block.html


def test_a_custom_slot_whose_fill_breaks_its_contract_twice_is_dropped_not_the_page(
    tmp_path: Path, kit_dist: Path
) -> None:
    def responder(request: LLMRequest) -> str:
        if request.purpose == "plan":
            return json.dumps(_with_custom(GOLDEN_OHM))
        if request.purpose == "fill":
            return 'fetch("https://example.com");'
        return fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder)
    events = collect("What happens to the current if I raise the resistance in a circuit?", deps)
    block = next(e for e in events if e.type == "environment").block
    assert block.lane == "instantiate" and "fetch" not in block.html
    refused = [r for r in trace_records(deps) if r["layer"] == "fill" and r["status"] == "refused"]
    assert len(refused) == 2 and "FILL-002" in refused[0]["detail"]["codes"]
    assert sum(c.purpose == "fill" for c in provider.calls) == 2


def test_an_unplannable_topic_in_fake_mode_still_answers_in_words(tmp_path: Path, kit_dist: Path) -> None:
    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    events = collect("How do enzymes change with temperature in the human body?", deps)
    assert "environment" not in kinds(events) and any(e.type == "text_delta" for e in events)
