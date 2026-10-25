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
from api.verify.mint import VerificationFailed, verify_environment
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
    assert kinds(events)[0] == "meta" and [k for k in kinds(events) if k not in ("probe", "exam")][-2:] == ["environment", "done"]
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
    assert last["outcome"] == "compose" and last["llm_calls"] == len(provider.calls)


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
    assert [k for k in kinds(events) if k not in ("probe", "exam")][-2:] == ["environment", "done"]
    assert len(attempts) == 2 and "PLAN-003" in attempts[1] and "PLAN-003" not in attempts[0]


def test_a_start_outside_its_range_is_repaired_without_asking_the_model_again(tmp_path: Path, kit_dist: Path) -> None:
    bad = json.loads(json.dumps(GOLDEN_SPRING))
    bad["controls"][0]["value"] = 99

    def responder(request: LLMRequest) -> str:
        return json.dumps(bad) if request.purpose == "plan" else fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder)
    events = collect(SPRING, deps)
    assert [k for k in kinds(events) if k not in ("probe", "exam")][-2:] == ["environment", "done"] and sum(c.purpose == "plan" for c in provider.calls) == 1


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
    assert block.lane == "compose" and "fetch" not in block.html
    refused = [r for r in trace_records(deps) if r["layer"] == "fill" and r["status"] == "refused"]
    assert len(refused) == 2 and "FILL-002" in refused[0]["detail"]["codes"]
    assert sum(c.purpose == "fill" for c in provider.calls) == 2


def test_an_unplannable_topic_in_fake_mode_still_answers_in_words(tmp_path: Path, kit_dist: Path) -> None:
    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    events = collect("How do enzymes change with temperature in the human body?", deps)
    assert "environment" not in kinds(events) and any(e.type == "text_delta" for e in events)


def test_a_refused_page_with_fills_is_retried_once_without_them(tmp_path: Path, kit_dist: Path) -> None:
    seen: list[str] = []

    def verify(**kw: object):  # noqa: ANN202
        html = str(kw["raw_html"])
        seen.append(html)
        if "Try moving each slider" in html:
            raise VerificationFailed("render", "dead_control", "the fill broke a control")
        return verify_environment(**kw)  # type: ignore[arg-type]

    def responder(request: LLMRequest) -> str:
        return json.dumps(_with_custom(GOLDEN_OHM)) if request.purpose == "plan" else fakes.fake_responder(request)

    deps, _ = deps_for(tmp_path, kit_dist, responder, verify_fn=verify)
    events = collect("What happens to the current if I raise the resistance in a circuit?", deps)
    block = next(e for e in events if e.type == "environment").block
    assert len(seen) == 2 and "Try moving each slider" not in block.html and block.lane == "compose"
    records = [r for r in trace_records(deps) if r["layer"] == "verify"]
    assert records[0]["status"] == "refused" and records[0]["detail"]["retry"] == "drop_fills"
    assert records[-1]["status"] == "ok"


# ── grounding: a Plan's citations decide the label (hard constraint 4) ─────────────────────────────────────────────────────

SYNTHETIC_DOC = "synthetic-physics"
SYNTHETIC_QUOTE = "In this made-up test passage a coiled wire grows longer in step with the weight it carries, until it is overloaded."


def grounded_deps(tmp_path: Path, kit_dist: Path, *, citation_ids: list[str], quote: str = SYNTHETIC_QUOTE, topics=None, models=None):  # noqa: ANN001, ANN201
    """A pipeline whose planner names `citation_ids`, over a SYNTHETIC corpus and pointer file (the real corpus is local and never in a test)."""
    from api.evidence.corpus import Corpus
    from api.evidence.registry import CitationBook

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / f"{SYNTHETIC_DOC}.jsonl").write_text(
        json.dumps({"page": 7, "text": f"Hooke's law. {SYNTHETIC_QUOTE} Next."}) + "\n", encoding="utf-8"
    )
    (corpus_dir / "citations.json").write_text(json.dumps({"quotes": {"hookes_synth": quote}}), encoding="utf-8")
    pointers = tmp_path / "pointers.json"
    pointers.write_text(
        json.dumps(
            {
                "pointers": {
                    "hookes_synth": {
                        "doc": SYNTHETIC_DOC,
                        "page": 7,
                        "claim": "extension is proportional to load",
                        "topics": topics or ["physics_form5_force_and_elasticity"],
                        "models": ["mechanics.hookes"] if models is None else models,
                        "checked_by": "synthetic test",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    book = CitationBook.load(Corpus.load(corpus_dir), corpus_dir, pointers)

    def responder(request: LLMRequest) -> str:
        if request.purpose == "plan":
            return json.dumps({**GOLDEN_SPRING, "citation_ids": citation_ids})
        return fakes.fake_responder(request)

    return deps_for(tmp_path, kit_dist, responder, evidence=book.evidence, citations=book)


def environment_of(events: list):  # noqa: ANN201
    return next(e.block for e in events if e.type == "environment")


def test_a_plan_whose_citation_the_corpus_proves_and_supports_is_minted_kit_verified_and_the_gate_re_proves_it(
    tmp_path: Path, kit_dist: Path
) -> None:
    deps, _ = grounded_deps(tmp_path, kit_dist, citation_ids=["hookes_synth"])
    block = environment_of(collect(SPRING, deps))
    assert block.label == "kit-verified"
    (citation,) = block.citations
    assert citation.verified and citation.source == SYNTHETIC_DOC and citation.page == 7 and citation.quote == SYNTHETIC_QUOTE
    ground = next(r for r in trace_records(deps) if r["layer"] == "ground")
    assert ground["status"] == "ok" and ground["detail"]["label"] == "kit-verified"
    # Delivery repeats the proof: with the corpus gone the same stored row is refused, not served on trust.
    from api.verify.gate import deliver

    stored_id = block.id
    refused = None
    try:
        deliver(deps.store, stored_id, public_origin=deps.public_origin, kit_dist=kit_dist, evidence=None)
    except Exception as exc:  # noqa: BLE001
        refused = exc
    assert refused is not None


@pytest.mark.parametrize(
    ("kwargs", "why"),
    [
        ({"citation_ids": ["no_such_citation"]}, "a citation did not prove"),
        ({"citation_ids": ["hookes_synth"], "quote": "A spring stretches in proportion to the load on it."}, "a citation did not prove"),
        ({"citation_ids": ["hookes_synth"], "topics": ["biology_form4_osmosis"], "models": []}, "a citation did not prove"),  # supports neither this topic nor this model
        ({"citation_ids": []}, "the plan names no citation"),
    ],
)
def test_a_citation_that_does_not_prove_or_does_not_support_the_plan_never_earns_kit_verified(
    tmp_path: Path, kit_dist: Path, kwargs: dict, why: str
) -> None:
    deps, _ = grounded_deps(tmp_path, kit_dist, **kwargs)
    block = environment_of(collect(SPRING, deps))
    assert block.label == "model-checked" and not block.citations[0].verified
    assert block.citations[0].source.startswith("UNVERIFIED (no textbook page has been checked")
    ground = next(r for r in trace_records(deps) if r["layer"] == "ground")
    assert ground["detail"]["why"] == why and ground["detail"]["label"] == "model-checked"


def test_without_a_corpus_the_label_and_the_citation_are_what_they_always_were(tmp_path: Path, kit_dist: Path) -> None:
    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    block = environment_of(collect(SPRING, deps))
    assert block.label == "model-checked" and block.citations[0].source == "UNVERIFIED (corpus not loaded until P2)"
    ground = next(r for r in trace_records(deps) if r["layer"] == "ground")
    assert ground["detail"]["why"] == "no corpus configured"


def test_a_refused_plan_leaves_the_checks_own_words_and_the_model_ids_in_the_trace(tmp_path: Path, kit_dist: Path) -> None:
    """The first real run without an exemplar failed with PLAN-002 and the trace kept only the code: which model had the planner invented? Now it says."""

    def invents_a_model(request: LLMRequest) -> str:
        if request.purpose == "plan":
            plan = json.loads(json.dumps(GOLDEN_SPRING))
            plan["models"][0]["model"] = "physics.spring_extension"
            return json.dumps(plan)
        return fakes.fake_responder(request)

    deps, _ = deps_for(tmp_path, kit_dist, invents_a_model)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and degraded(events)
    refused = [r for r in trace_records(deps) if r["layer"] == "plan_checks" and r["status"] == "refused"]
    assert len(refused) == 2  # the attempt and its one retry
    for record in refused:
        assert "PLAN-002" in record["detail"]["codes"]
        assert record["detail"]["models"] == ["physics.spring_extension"]
        assert any("physics.spring_extension" in note for note in record["detail"]["issues"])


def test_a_request_over_the_token_cap_degrades_to_words_and_sends_nothing(
    tmp_path: Path, kit_dist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cap check used to raise out of the pipeline as an internal error. Now the student gets the written answer and the trace says why."""
    from api.pipeline import prompts

    monkeypatch.setattr(prompts, "REQUEST_TOKEN_CAP", 3000)  # above the small route and explain requests, below the plan request
    deps, provider = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and "error" not in kinds(events) and degraded(events)
    assert not [c for c in provider.calls if c.purpose == "plan"]  # nothing was sent for the plan
    assert any(r["status"] == "request_too_large" for r in trace_records(deps))
