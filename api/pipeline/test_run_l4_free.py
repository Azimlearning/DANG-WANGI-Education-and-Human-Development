"""L4, the wording check, and the Free lane inside the orchestrator (D-41). All on fakes: nothing here can spend money or open a socket. The Free
lane cases that get as far as the verifier run the page in real Chromium."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.llm.providers.fake import FakeProvider
from api.llm.types import LLMRequest
from api.pipeline import fakes, run
from api.pipeline.test_run import (
    GOLDEN_SPRING,
    SPRING,
    collect,
    degraded,
    deps_for,
    kinds,
    trace_records,
)


def purposes(provider: FakeProvider) -> list[str]:
    return [c.purpose for c in provider.calls]


def gap_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def environment_of(events: list):  # noqa: ANN201
    return next(e for e in events if e.type == "environment").block


def marked_plan() -> str:
    """The golden spring Plan with the fake judge's test marker in its note."""
    plan = json.loads(json.dumps(GOLDEN_SPRING))
    plan["note"] = f"{fakes.FALSE_MARKER} " + plan["note"][:300]
    return json.dumps(plan)


def failing_planner(request: LLMRequest) -> str:
    return "{}" if request.purpose == "plan" else fakes.fake_responder(request)


def free_with(page: str):  # noqa: ANN201
    """A responder whose planner always fails (so the Kit cannot take the question) and whose Free generator returns `page`."""

    def responder(request: LLMRequest) -> str:
        if request.purpose == "plan":
            return "{}"
        if request.purpose == "free":
            return page
        return fakes.fake_responder(request)

    return responder


def good_page() -> str:
    return fakes.free_responder(None)  # type: ignore[arg-type]


# ── L4 on a Compose Plan ──────────────────────────────────────────────────────────────────────────────────────────────


def test_the_call_budget_leaves_room_for_two_checked_plans_and_one_free_page() -> None:
    assert run.MAX_LLM_CALLS == 8


def test_without_the_wording_check_no_judge_is_called_and_no_layer_is_claimed(tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    block = environment_of(collect(SPRING, deps))
    assert not {"wording", "wording_free", "free"} & set(purposes(provider))
    assert "wording" not in block.checked.layers


def test_a_judge_that_passes_the_words_adds_the_layer_to_what_the_student_is_shown(tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, fakes.fake_responder, wording_check=True)
    block = environment_of(collect(SPRING, deps))
    assert purposes(provider).count("wording") == 1
    assert block.checked.layers[-1] == "wording"
    plan_ok = next(r for r in trace_records(deps) if r["layer"] == "plan_checks" and r["status"] == "ok")
    assert plan_ok["detail"]["wording"] == "checked"


def test_a_refused_wording_goes_back_to_the_planner_once_with_the_named_issue_then_the_page_is_made(
    tmp_path: Path, kit_dist: Path
) -> None:
    attempts: list[str] = []

    def responder(request: LLMRequest) -> str:
        if request.purpose == "plan":
            attempts.append(request.prompt)
            return marked_plan() if len(attempts) == 1 else json.dumps(GOLDEN_SPRING)
        return fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder, wording_check=True)
    block = environment_of(collect(SPRING, deps))
    assert purposes(provider)[-4:] == ["plan", "wording", "plan", "wording"]
    assert "L4-001" in attempts[1] and "planted false statement" in attempts[1] and "L4-001" not in attempts[0]
    assert "wording" in block.checked.layers
    refused = [r for r in trace_records(deps) if r["layer"] == "plan_checks" and r["status"] == "refused"]
    assert refused and refused[0]["detail"]["codes"] == ["L4-001"]


def test_a_plan_the_judge_refuses_twice_degrades_to_the_written_answer_and_the_gap_is_logged(
    tmp_path: Path, kit_dist: Path
) -> None:
    def responder(request: LLMRequest) -> str:
        return marked_plan() if request.purpose == "plan" else fakes.fake_responder(request)

    gaps = tmp_path / "gaps.jsonl"
    deps, provider = deps_for(tmp_path, kit_dist, responder, wording_check=True, gap_log_path=gaps)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and degraded(events)
    assert purposes(provider).count("wording") == 2 and "free" not in purposes(provider)
    rows = gap_rows(gaps)
    # Not a Kit gap: the Kit could express it and the prose was refused. It is logged as what it is.
    assert len(rows) == 1 and rows[0]["reason"] == "wording_refused" and rows[0]["outcome"] == "text_only"
    assert SPRING not in gaps.read_text(encoding="utf-8")


def test_under_the_kit_preference_a_twice_refused_plan_still_ends_with_a_lab_from_the_last_step(tmp_path: Path, kit_dist: Path) -> None:
    # W20 (D-80): the `kit` preference no longer lets a question end without a lab. The Free lane does not take over in the middle of the pipeline,
    # but the last step writes a page for the question, with every Free check.
    def responder(request: LLMRequest) -> str:
        return marked_plan() if request.purpose == "plan" else fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder, wording_check=True, free_lane=True, lane_preference="kit")
    events = collect(SPRING, deps)
    assert environment_of(events).lane == "free"
    calls = purposes(provider)
    assert calls.index("free") > max(i for i, p in enumerate(calls) if p == "wording")  # only after both plans were refused
    assert "wording_free" in calls


def test_a_wording_refusal_goes_on_to_the_free_lane_under_the_balanced_preference(tmp_path: Path, kit_dist: Path) -> None:
    # W19 (D-76): the owner leans the pipeline towards Free; a Kit plan whose words were refused twice gets a whole page, read by its own second reader.
    def responder(request: LLMRequest) -> str:
        return marked_plan() if request.purpose == "plan" else fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder, wording_check=True, free_lane=True, lane_preference="balanced")
    collect(SPRING, deps)
    assert "free" in purposes(provider)


@pytest.mark.parametrize("reply", ["maybe", "{}", '{"ok": true}', ""])
def test_a_judge_with_no_usable_verdict_never_earns_the_layer_and_never_blocks_the_page(
    tmp_path: Path, kit_dist: Path, reply: str
) -> None:
    def responder(request: LLMRequest) -> str:
        return reply if request.purpose == "wording" else fakes.fake_responder(request)

    deps, _ = deps_for(tmp_path, kit_dist, responder, wording_check=True)
    block = environment_of(collect(SPRING, deps))
    assert "wording" not in block.checked.layers
    assert next(r for r in trace_records(deps) if r["layer"] == "wording")["status"] == "unreadable"
    plan_ok = next(r for r in trace_records(deps) if r["layer"] == "plan_checks" and r["status"] == "ok")
    assert plan_ok["detail"]["wording"] == "not checked"


def test_a_judge_over_the_call_budget_is_unavailable_not_a_pass(
    tmp_path: Path, kit_dist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plain, counted = deps_for(tmp_path / "plain", kit_dist, fakes.fake_responder)
    collect(SPRING, plain)
    # The calls a run makes WITHOUT the judge (explain, plan, and a routing fallback if one was needed) use the whole budget, so the judge has no call left.
    monkeypatch.setattr(run, "MAX_LLM_CALLS", len(counted.calls))
    deps, _ = deps_for(tmp_path / "judged", kit_dist, fakes.fake_responder, wording_check=True)
    events = collect(SPRING, deps)
    assert next(r for r in trace_records(deps) if r["layer"] == "wording")["status"] == "unavailable"
    if "environment" in kinds(events):
        assert "wording" not in environment_of(events).checked.layers


# ── the Kit gap log ───────────────────────────────────────────────────────────────────────────────────────────────────


def test_with_the_free_lane_off_a_question_the_kit_cannot_take_is_logged_as_a_gap_and_answered_in_words(
    tmp_path: Path, kit_dist: Path
) -> None:
    gaps = tmp_path / "gaps.jsonl"
    deps, provider = deps_for(tmp_path, kit_dist, failing_planner, gap_log_path=gaps)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and "free" not in purposes(provider)
    rows = gap_rows(gaps)
    assert len(rows) == 1 and rows[0]["outcome"] == "text_only" and rows[0]["reason"].startswith("plan_failed")
    assert rows[0]["question_sha256"] and rows[0]["topic"] and rows[0]["pattern"]


def test_an_assembly_gap_is_logged_with_the_part_that_is_missing(
    tmp_path: Path, kit_dist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def gap(*_a: object, **_k: object) -> None:
        raise run.AssemblyGap("lens_scene", "no slot for a lens")

    monkeypatch.setattr(run, "assemble", gap)
    gaps = tmp_path / "gaps.jsonl"
    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder, gap_log_path=gaps)
    assert "environment" not in kinds(collect(SPRING, deps))
    assert gap_rows(gaps)[0]["reason"] == "assembly_gap:lens_scene"


# ── the Free lane ─────────────────────────────────────────────────────────────────────────────────────────────────────


def test_the_free_lane_delivers_a_labelled_whole_page_for_a_question_the_kit_cannot_take(
    tmp_path: Path, kit_dist: Path
) -> None:
    gaps = tmp_path / "gaps.jsonl"
    deps, provider = deps_for(tmp_path, kit_dist, failing_planner, free_lane=True, wording_check=True, gap_log_path=gaps)
    block = environment_of(collect(SPRING, deps))
    assert block.lane == "free" and block.label == "model-checked"
    assert list(block.checked.layers) == ["postprocess", "scan", "render", "wording"]
    assert block.citations and not any(c.verified for c in block.citations) and "UNVERIFIED" in block.citations[0].source
    assert block.checked.limits.startswith("Written whole by a model") and "second model read" in block.checked.limits
    assert "/vendor/kit/" not in block.html
    assert purposes(provider).count("free") == 1 and purposes(provider).count("wording_free") == 1
    rows = gap_rows(gaps)
    assert len(rows) == 1 and rows[0]["outcome"] == "free" and rows[0]["env_id"] == block.id
    assert json.loads(deps.trace_path.read_text().splitlines()[-1])["outcome"] == "free"  # type: ignore[union-attr]


def test_a_free_page_is_remembered_for_the_same_question_and_served_again_through_the_gate(
    tmp_path: Path, kit_dist: Path
) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, failing_planner, free_lane=True, wording_check=True)
    first = environment_of(collect(SPRING, deps))
    before = len(provider.calls)
    second = environment_of(collect(SPRING, deps))
    assert second.id == first.id and second.lane == "free"
    assert "free" not in purposes(provider)[before:] and "plan" not in purposes(provider)[before:]


def test_a_free_page_the_judge_refuses_is_never_shown(tmp_path: Path, kit_dist: Path) -> None:
    page = good_page().replace("Double the depth", fakes.FALSE_MARKER)
    gaps = tmp_path / "gaps.jsonl"
    deps, _ = deps_for(tmp_path, kit_dist, free_with(page), free_lane=True, wording_check=True, gap_log_path=gaps)
    assert "environment" not in kinds(collect(SPRING, deps))
    records = [r for r in trace_records(deps) if r["layer"] == "free"]
    # W20: the first refusal is retried once with the reader's issues; the second is final for the full page
    assert records[0]["status"] == "retry" and records[0]["detail"]["why"] == "reader"
    assert next(r for r in records if r["status"] == "refused")["detail"]["code"] == "L4-001"
    assert not any(r["layer"] == "verify" for r in trace_records(deps))
    assert gap_rows(gaps)[0]["outcome"] == "text_only"


def test_a_free_page_with_no_usable_judge_is_never_shown(tmp_path: Path, kit_dist: Path) -> None:
    inner = free_with(good_page())

    def responder(request: LLMRequest) -> str:
        return "no idea" if request.purpose == "wording_free" else inner(request)

    deps, _ = deps_for(tmp_path, kit_dist, responder, free_lane=True, wording_check=True)
    assert "environment" not in kinds(collect(SPRING, deps))
    assert next(r for r in trace_records(deps) if r["layer"] == "free")["detail"]["code"] == "FREE-002"


def test_a_reply_that_is_not_a_document_is_refused_as_free_001(tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, free_with("Sorry, I can only explain this in words."), free_lane=True, wording_check=True)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events)
    # W19: the first non-document is retried once with the reason; the second is refused as FREE-001, and the judge is never paid for either.
    free_records = [r for r in trace_records(deps) if r["layer"] == "free"]
    assert free_records[0]["status"] == "retry"
    assert next(r for r in free_records if r["status"] == "refused")["detail"]["code"] == "FREE-001"
    # W20 (D-80): then the last step writes up to three simple pages, each after the first told why the one before was refused.
    writes = [c for c in provider.calls if c.purpose == "free"]
    assert len(writes) == 2 + run.SIMPLE_ATTEMPTS
    assert all("was refused: the reply was not the lab in the @@ sections asked for" in c.prompt for c in writes[3:])
    assert "wording_free" not in purposes(provider)
    assert degraded(events)[-1].note == run.NO_LAB_NOTE


def test_the_cheap_scan_runs_before_the_judge_is_paid(tmp_path: Path, kit_dist: Path) -> None:
    page = good_page().replace("show();\n})();", 'show();\n  fetch("/x");\n})();')
    assert "fetch(" in page
    deps, provider = deps_for(tmp_path, kit_dist, free_with(page), free_lane=True, wording_check=True)
    assert "environment" not in kinds(collect(SPRING, deps))
    assert "wording_free" not in purposes(provider)  # nothing was spent judging a page the scan would refuse
    assert next(r for r in trace_records(deps) if r["layer"] == "free")["detail"]["rule"] == "forbidden_api"


def test_the_free_lane_does_nothing_and_spends_nothing_when_no_second_reader_is_configured(tmp_path: Path, kit_dist: Path) -> None:
    gaps = tmp_path / "gaps.jsonl"
    deps, provider = deps_for(tmp_path, kit_dist, failing_planner, free_lane=True, gap_log_path=gaps)  # wording_check stays off, as in fake mode
    assert "environment" not in kinds(collect(SPRING, deps))
    assert not {"free", "wording_free"} & set(purposes(provider))
    assert next(r for r in trace_records(deps) if r["layer"] == "free")["detail"]["code"] == "FREE-002"
    assert gap_rows(gaps)[0]["outcome"] == "text_only"


def test_a_free_page_whose_control_changes_nothing_is_refused_by_the_real_browser_run(tmp_path: Path, kit_dist: Path) -> None:
    page = good_page().replace('out.textContent = pressureKpa(h).toFixed(1) + " kPa";', 'out.textContent = "fixed";')
    assert '"fixed"' in page
    deps, _ = deps_for(tmp_path, kit_dist, free_with(page), free_lane=True, wording_check=True)
    assert "environment" not in kinds(collect(SPRING, deps))
    refused = next(r for r in trace_records(deps) if r["layer"] == "verify")
    assert refused["status"] == "refused" and refused["detail"]["lane"] == "free" and refused["detail"]["rule"] == "dead_control"


# ── fixes from the reviews of 2026-10-22 ──────────────────────────────────────────────────────────────────────────────


def test_a_page_with_a_slot_fill_does_not_claim_the_wording_layer_because_the_judge_never_read_the_fill(
    tmp_path: Path, kit_dist: Path
) -> None:
    from api.pipeline.test_run import GOLDEN_OHM, _with_custom

    def responder(request: LLMRequest) -> str:
        return json.dumps(_with_custom(GOLDEN_OHM)) if request.purpose == "plan" else fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder, wording_check=True)
    block = environment_of(collect("What happens to the current if I raise the resistance in a circuit?", deps))
    assert purposes(provider).count("wording") == 1  # the Plan was read...
    assert "Try moving each slider" in block.html  # ...but the fill was written after, and is on the page
    assert "wording" not in block.checked.layers


def test_a_free_page_too_big_to_be_read_whole_is_refused_and_the_judge_is_not_paid(tmp_path: Path, kit_dist: Path) -> None:
    page = good_page().replace("<h1>", "".join(f"<p>filler line {i}</p>" for i in range(200)) + "<h1>")
    deps, provider = deps_for(tmp_path, kit_dist, free_with(page), free_lane=True, wording_check=True)
    assert "environment" not in kinds(collect(SPRING, deps))
    records = [r for r in trace_records(deps) if r["layer"] == "free"]
    assert records[0]["status"] == "retry" and records[0]["detail"]["why"] == "too long"  # W20: told to write it shorter, once
    refused = next(r for r in records if r["status"] == "refused")
    assert refused["detail"]["code"] == "FREE-001" and "lines of text" in refused["detail"]["why"]
    assert "wording_free" not in purposes(provider)


def test_a_free_page_is_not_paid_for_when_its_reading_would_not_fit_under_the_cap(tmp_path: Path, kit_dist: Path) -> None:
    from api.llm.ledger import SpendLedger, engine_for
    from api.llm.models import ANTHROPIC_MODELS
    from api.llm.service import LLMService

    deps, _ = deps_for(tmp_path, kit_dist, failing_planner, free_lane=True, wording_check=True)
    priced = FakeProvider(failing_planner, name="anthropic", models=ANTHROPIC_MODELS)
    deps.llm = LLMService(priced, None, SpendLedger(engine_for(tmp_path / "capped.db"), 0.065))  # the page alone would fit, the page and its reading would not
    assert "environment" not in kinds(collect(SPRING, deps))
    assert "free" not in purposes(priced)  # nothing was spent on a page that could not be read
    assert next(r for r in trace_records(deps) if r["layer"] == "free")["detail"]["code"] == "PIPE-002"


def rejecting(purpose: str, *, planner_fails: bool):  # noqa: ANN201
    from api.llm.providers.base import ProviderFailure

    def responder(request: LLMRequest) -> str:
        if request.purpose == purpose:
            raise ProviderFailure("fake", "the key was refused", "auth")
        return failing_planner(request) if planner_fails else fakes.fake_responder(request)

    return responder


def test_a_provider_that_rejects_the_judge_call_stops_the_request_and_is_not_swallowed(tmp_path: Path, kit_dist: Path) -> None:
    deps, _ = deps_for(tmp_path, kit_dist, rejecting("wording", planner_fails=False), wording_check=True)
    events = collect(SPRING, deps)
    assert "error" in kinds(events) and "environment" not in kinds(events)


def test_a_gap_is_logged_even_when_the_free_attempt_ends_in_an_error(tmp_path: Path, kit_dist: Path) -> None:
    gaps = tmp_path / "gaps.jsonl"
    deps, _ = deps_for(
        tmp_path, kit_dist, rejecting("free", planner_fails=True), free_lane=True, wording_check=True, gap_log_path=gaps
    )
    events = collect(SPRING, deps)
    assert "error" in kinds(events) and "environment" not in kinds(events)
    assert [r["outcome"] for r in gap_rows(gaps)] == ["error"]


# ── the last step: a lab for every question (W20, D-80) ────────────────────────────────────────────────────────────────


def marked_page() -> str:
    """A good page whose words carry the fake judge's refusal marker."""
    return good_page().replace("</body>", f"<p>{fakes.FALSE_MARKER} planted</p></body>", 1)


def full_refused_simple_good(request: LLMRequest) -> str:
    """The planner fails, the full page is refused by the reader, and the simple page (its pack says a fuller lab could not be made) is good."""
    if request.purpose == "plan":
        return "{}"
    if request.purpose == "free":
        return good_page() if "A fuller lab could not be made" in (request.system or "") else marked_page()
    return fakes.fake_responder(request)


def test_a_full_page_refused_by_the_reader_is_followed_by_a_simple_lab_that_is_delivered(tmp_path: Path, kit_dist: Path) -> None:
    gaps = tmp_path / "gaps.jsonl"
    deps, provider = deps_for(tmp_path, kit_dist, full_refused_simple_good, free_lane=True, wording_check=True, gap_log_path=gaps)
    events = collect(SPRING, deps)
    block = environment_of(events)
    assert block.lane == "free" and block.label == "model-checked" and "wording" in block.checked.layers
    assert any(e.type == "stage" and e.note == run.SIMPLE_NOTE for e in events)
    assert purposes(provider).count("wording_free") == 3  # the full page and its one retry (both refused), then the simple page
    assert next(r for r in trace_records(deps) if r["layer"] == "simple" and r["status"] == "ok")
    assert gap_rows(gaps)[-1]["reason"] == "simple" and gap_rows(gaps)[-1]["env_id"] == block.id


def test_the_simple_page_after_a_reader_refusal_is_told_what_the_reader_found(tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, free_with(marked_page()), free_lane=True, wording_check=True)
    events = collect(SPRING, deps)
    assert "environment" not in kinds(events) and degraded(events)[-1].note == run.NO_LAB_NOTE
    simple = [c for c in provider.calls if c.purpose == "free" and "A fuller lab could not be made" in (c.system or "")]
    assert len(simple) == run.SIMPLE_ATTEMPTS
    assert "a second reader found these problems" in simple[1].prompt and "planted false statement" in simple[1].prompt


def test_a_compose_page_refused_in_the_browser_gets_the_full_page_from_the_last_step(tmp_path: Path, kit_dist: Path) -> None:
    from api.verify.mint import VerificationFailed, verify_environment

    def verify(**kw: object):  # noqa: ANN202
        if kw["lane"] == "compose":
            raise VerificationFailed("render", "dead_control", "control 'load' changed no readout")
        return verify_environment(**kw)  # type: ignore[arg-type]

    deps, provider = deps_for(tmp_path, kit_dist, fakes.fake_responder, free_lane=True, wording_check=True, verify_fn=verify, lane_preference="kit")
    block = environment_of(collect(SPRING, deps))
    assert block.lane == "free"
    assert purposes(provider).count("free") == 1  # the full page, not the simple one: it was never tried before


def test_a_question_outside_science_still_gets_a_lab(tmp_path: Path, kit_dist: Path) -> None:
    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder, free_lane=True, wording_check=True)
    events = collect("What is the capital city of France?", deps)
    assert environment_of(events).lane == "free"


def test_without_a_second_reader_the_last_step_spends_nothing(tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, failing_planner, free_lane=True)
    assert "environment" not in kinds(collect(SPRING, deps))
    assert "free" not in purposes(provider)


def test_the_heavy_tier_writes_plans_and_pages_with_room_to_think_and_leaves_the_readers_alone(tmp_path: Path, kit_dist: Path) -> None:
    from api.llm.types import MAX_OUTPUT_TOKENS
    from api.pipeline import prompts

    deps, provider = deps_for(tmp_path, kit_dist, failing_planner, free_lane=True, wording_check=True, generation_tier="heavy")
    collect(SPRING, deps)
    by = {c.purpose: c for c in provider.calls}
    assert by["plan"].tier == "heavy" and by["plan"].max_tokens == prompts.PLAN_MAX_TOKENS * prompts.HEAVY_TOKEN_FACTOR and by["plan"].effort == "medium"
    assert by["free"].tier == "heavy" and by["free"].max_tokens == min(prompts.FREE_MAX_TOKENS * prompts.HEAVY_TOKEN_FACTOR, MAX_OUTPUT_TOKENS)  # the service refuses more
    assert by["wording_free"].tier == "standard" and by["explain"].tier == "standard"


def test_a_partial_fit_whose_full_page_fails_gets_a_simple_lab_on_the_question_before_the_kit_lab(tmp_path: Path, kit_dist: Path) -> None:
    # W20 (D-81): a quantum question once got a Boyle's law syringe, because the Kit lab for a partial fit came before a simple lab on the question itself.
    def responder(request: LLMRequest) -> str:
        if request.purpose == "plan":
            plan = json.loads(json.dumps(GOLDEN_SPRING))
            plan["fit"], plan["missing"] = "partial", "The Kit has no model for this question."
            return json.dumps(plan)
        return full_refused_simple_good(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder, free_lane=True, wording_check=True)
    events = collect(SPRING, deps)
    block = environment_of(events)
    assert block.lane == "free"
    assert not any(r["layer"] == "lane" and r["status"] == "kit_fallback" for r in trace_records(deps))
    assert any(e.type == "stage" and e.note == run.SIMPLE_NOTE for e in events)


def test_a_full_page_refused_in_the_browser_is_written_once_more_with_the_reason_and_delivered(tmp_path: Path, kit_dist: Path) -> None:
    # W20 (D-81): the quantum page failed only because one slider moved no readout; the retry is told which check failed and why.
    dead = good_page().replace('out.textContent = pressureKpa(h).toFixed(1) + " kPa";', 'out.textContent = "fixed";')

    def responder(request: LLMRequest) -> str:
        if request.purpose == "plan":
            return "{}"
        if request.purpose == "free":
            return good_page() if "real-browser check refused it" in request.prompt else dead
        return fakes.fake_responder(request)

    deps, provider = deps_for(tmp_path, kit_dist, responder, free_lane=True, wording_check=True)
    block = environment_of(collect(SPRING, deps))
    assert block.lane == "free"
    writes = [c for c in provider.calls if c.purpose == "free"]
    assert len(writes) == 2 and "dead_control" in writes[1].prompt
    assert any(r["layer"] == "free" and r["status"] == "retry" and r["detail"].get("why") == "browser" for r in trace_records(deps))
