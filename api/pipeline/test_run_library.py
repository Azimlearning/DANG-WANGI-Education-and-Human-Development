"""W2 (D-42): a covered question is answered from the library with NO model call, and anything the library cannot serve falls through to the normal pipeline.
Everything runs on fakes; the provider spy proves that nothing was sent."""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path

import pytest

from api.pipeline import fakes, library
from api.pipeline.test_run import collect, deps_for, kinds, trace_records
from api.verify.store import SqliteEnvironmentStore
from eval.golden.run import load as load_golden

REPO = Path(__file__).resolve().parents[2]
SEEDED = {"hookes_amali", "ohm_explorer"}
GOLDEN = {q["id"]: q["question"] for q in load_golden()}
# Measured with the local router alone (2026-10-23): g01 and g09 are recognised at 0.94 and 0.98; g04 is the right topic at only 0.40, below the threshold;
# g17 is confident but its topic (liquid pressure) is not in the seeded set used here.
SPRING, OHM, LOW_CONFIDENCE, NOT_SEEDED = GOLDEN["g01"], GOLDEN["g09"], GOLDEN["g04"], GOLDEN["g17"]


def plan_note(plan_id: str) -> str:
    for path in (REPO / "data" / "plans").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["id"] == plan_id:
            return data["note"]
    raise AssertionError(plan_id)


@pytest.fixture(scope="module")
def seeded_db(kit_dist: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("library") / "seeded.db"
    store = SqliteEnvironmentStore(path)
    built = library.seed(store, kit_dist=kit_dist, public_origin="http://localhost:3000", interaction_seconds=1.0, only=SEEDED)
    assert {plan.id for plan, _ in built} == SEEDED
    return path


def seeded_deps(seeded_db: Path, tmp_path: Path, kit_dist: Path, responder=fakes.fake_responder, **extra):  # noqa: ANN001, ANN201
    shutil.copy(seeded_db, tmp_path / "envs.db")  # each test gets its own copy: withdrawing or remembering in one must not leak into another
    return deps_for(tmp_path, kit_dist, responder, **extra)


def words(events: list) -> str:
    return "".join(e.text for e in events if e.type == "text_delta")


# ── the store ─────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_a_store_made_before_the_answer_column_is_migrated_and_keeps_its_questions(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE questions (canon TEXT PRIMARY KEY, env_id TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("INSERT INTO questions VALUES ('why spring', 'env-1', '2026-10-01')")
    db.commit()
    db.close()
    store = SqliteEnvironmentStore(path)
    assert store.lookup_question_entry("why spring") == ("env-1", None)  # an old entry has no kept words
    store.remember_question("why spring", "env-2", "Because springs stretch.")
    assert store.lookup_question_entry("why spring") == ("env-2", "Because springs stretch.")
    assert store.lookup_question("why spring") == "env-2" and store.lookup_question_entry("never asked") is None


def test_only_a_stored_verified_environment_can_be_indexed_under_a_topic(tmp_path: Path) -> None:
    store = SqliteEnvironmentStore(tmp_path / "s.db")
    with pytest.raises(KeyError):
        store.index_topic("physics_form5_x", "no-such-env", plan_id="p", title="t", goal="g", note="n")
    assert store.topic_entries("physics_form5_x") == []


def test_the_seeded_library_is_indexed_by_each_plans_topic_with_its_own_words(seeded_db: Path) -> None:
    store = SqliteEnvironmentStore(seeded_db)
    entries = store.topic_entries("physics_form5_force_and_elasticity")
    assert [e["plan_id"] for e in entries] == ["hookes_amali"] and entries[0]["note"] == plan_note("hookes_amali")
    assert store.topic_entries("physics_form5_forces_and_pressure") == []  # not seeded in this fixture


def test_best_entry_prefers_the_environment_that_shares_the_most_words_and_is_stable_on_a_tie() -> None:
    entries = [
        {"env_id": "a", "plan_id": "alpha", "title": "Pressure in a liquid", "goal": "depth and pressure", "note": "n"},
        {"env_id": "b", "plan_id": "beta", "title": "Current in a circuit", "goal": "resistance and current", "note": "n"},
    ]
    assert library.best_entry("how does resistance change the current", entries)["env_id"] == "b"
    assert library.best_entry("something unrelated", entries)["env_id"] == "a"  # a tie keeps the first


# ── the pipeline ──────────────────────────────────────────────────────────────────────────────────────────────────────


def test_a_question_the_local_router_recognises_is_answered_from_the_library_with_no_model_call(
    seeded_db: Path, tmp_path: Path, kit_dist: Path
) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist)
    events = collect(SPRING, deps)
    assert provider.calls == [], "a covered topic must cost nothing: no routing call, no explanation, no plan"
    block = next(e for e in events if e.type == "environment").block
    assert block.lane == "instantiate" and block.id.startswith("hookes_amali-")
    assert words(events) == plan_note("hookes_amali")  # the hand-written Plan's own words, not a model's
    assert [k for k in kinds(events) if k not in ("probe", "exam")][-2:] == ["environment", "done"]
    library_record = next(r for r in trace_records(deps) if r["layer"] == "library")
    # W19: the seed remembers the questions a lab is known to answer, so this one is served as a known question, before the router is even asked
    assert library_record["status"] == "hit" and library_record["detail"]["kind"] in ("question", "topic")
    assert json.loads(deps.trace_path.read_text().splitlines()[-1])["outcome"] == "library:instantiate"  # type: ignore[union-attr]


def test_the_nearest_environment_of_the_recognised_topic_is_the_one_served(seeded_db: Path, tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist)
    block = next(e for e in collect(OHM, deps) if e.type == "environment").block
    assert provider.calls == [] and block.id.startswith("ohm_explorer-")


def test_a_hit_is_served_in_under_a_second_once_the_router_is_loaded(seeded_db: Path, tmp_path: Path, kit_dist: Path) -> None:
    deps, _ = seeded_deps(seeded_db, tmp_path, kit_dist)
    collect(SPRING, deps)  # loads the router model and the Kit manifest; the first request of a process pays for that
    started = time.monotonic()
    events = collect(OHM, deps)
    elapsed = time.monotonic() - started
    assert "environment" in kinds(events) and elapsed < 1.0, f"a covered topic took {elapsed:.2f} s"


def reworded_spring_plan(request) -> str:  # noqa: ANN001
    """The fake planner, but with a different note so the page is NOT byte for byte the library's."""
    if request.purpose != "plan":
        return fakes.fake_responder(request)
    plan = json.loads(fakes.fake_responder(request))
    plan["note"] = plan["note"] + " Try small loads first."
    return json.dumps(plan)


def test_a_topic_recognised_below_the_confidence_threshold_goes_the_normal_way(seeded_db: Path, tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist, reworded_spring_plan)
    library_id = deps.store.topic_entries("physics_form5_force_and_elasticity")[0]["env_id"]
    block = next(e for e in collect(LOW_CONFIDENCE, deps) if e.type == "environment").block
    assert {"explain", "plan"} <= {c.purpose for c in provider.calls}
    assert block.lane == "compose" and block.id != library_id


def test_a_page_identical_to_a_library_page_is_delivered_as_the_stored_one_not_a_crash(seeded_db: Path, tmp_path: Path, kit_dist: Path) -> None:
    """The fake planner reproduces the hand-written Plan, so the generated page is byte for byte the library's. The stored claim (Instantiate) stands."""
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist)
    events = collect(LOW_CONFIDENCE, deps)
    block = next(e for e in events if e.type == "environment").block
    assert {"explain", "plan"} <= {c.purpose for c in provider.calls}
    assert block.lane == "instantiate" and block.id.startswith("hookes_amali-")
    assert next(r for r in trace_records(deps) if r["layer"] == "deliver")["status"] == "existing"


def test_a_confident_topic_with_nothing_seeded_goes_the_normal_way(seeded_db: Path, tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist)
    events = collect(NOT_SEEDED, deps)
    assert {"explain", "plan"} <= {c.purpose for c in provider.calls} and "environment" in kinds(events)


def test_a_withdrawn_library_environment_is_not_served_and_the_pipeline_makes_a_new_one(
    seeded_db: Path, tmp_path: Path, kit_dist: Path
) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist, reworded_spring_plan)
    entry = deps.store.topic_entries("physics_form5_force_and_elasticity")[0]
    deps.store.withdraw(entry["env_id"], "test: wrong science")
    block = next(e for e in collect(SPRING, deps) if e.type == "environment").block
    assert provider.calls, "the gate refused the stored Environment, so the normal pipeline had to run"
    assert block.lane == "compose" and block.id != entry["env_id"]
    refused = next(r for r in trace_records(deps) if r["layer"] == "library")
    assert refused["status"] == "refused" and refused["detail"]["rule"] == "withdrawn"


def test_a_withdrawn_page_stays_withdrawn_when_a_planner_reproduces_it_byte_for_byte(seeded_db: Path, tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist)
    entry = deps.store.topic_entries("physics_form5_force_and_elasticity")[0]
    deps.store.withdraw(entry["env_id"], "test: wrong science")
    events = collect(SPRING, deps)
    assert provider.calls and "environment" not in kinds(events)  # the same bytes were withdrawn, so a regenerated copy is not delivered either
    delivery = [r for r in trace_records(deps) if r["layer"] == "deliver"]
    assert [r["status"] for r in delivery] == ["existing", "refused"] and delivery[-1]["detail"]["rule"] == "withdrawn"


def test_without_the_router_nothing_is_served_by_topic(seeded_db: Path, tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist, use_router=False)
    collect("Why does a spring get longer when more weight hangs from it?", deps)  # not one of the remembered questions (W19)
    assert provider.calls  # the library is skipped and the pipeline runs


def test_a_repeated_question_costs_no_model_call_and_brings_back_the_same_words(tmp_path: Path, kit_dist: Path) -> None:
    deps, provider = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    first = collect(LOW_CONFIDENCE, deps)  # generated: the topic is recognised too weakly for the library
    spent = len(provider.calls)
    assert spent >= 2 and words(first)
    second = collect(LOW_CONFIDENCE, deps)
    assert len(provider.calls) == spent, "the repeat must not call the model, not even to explain"
    assert words(second) == words(first)
    assert next(e for e in second if e.type == "environment").block.id == next(e for e in first if e.type == "environment").block.id
    assert next(r for r in trace_records(deps) if r["layer"] == "library")["detail"]["words"] == "kept"


def test_a_budget_placeholder_is_never_kept_as_the_answer(tmp_path: Path, kit_dist: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from api.pipeline import run

    monkeypatch.setattr(run, "MAX_LLM_CALLS", 0)  # even the explanation is over budget
    deps, _ = deps_for(tmp_path, kit_dist, fakes.fake_responder)
    collect(LOW_CONFIDENCE, deps)
    assert deps.store.lookup_question_entry(run.canonical_question(LOW_CONFIDENCE)) is None  # nothing was delivered, so nothing is cached


# ── a question that names an Environment (D-59) ────────────────────────────────


NAMED = [
    {"env_id": "a", "plan_id": "hookes_amali", "title": "Hooke's law: how does a spring stretch?", "goal": "See how a spring stretches under a load.", "note": "n"},
    {"env_id": "b", "plan_id": "newton_cannonball", "title": "Newton's cannonball: falling, orbiting and escaping", "goal": "Launch a cannonball at different speeds.", "note": "n"},
    {"env_id": "c", "plan_id": "newton_second_lab", "title": "Newton's second law: force, mass and acceleration", "goal": "See how force changes acceleration.", "note": "n"},
    {"env_id": "d", "plan_id": "yeast_fermentation_lab", "title": "Yeast fermentation: the products and the energy", "goal": "See what yeast makes.", "note": "n"},
]


@pytest.mark.parametrize(
    ("question", "plan_id"),
    [
        ("How do I revise Hooke's law?", "hookes_amali"),
        ("Show Newton's cannonball for my class", "newton_cannonball"),
        ("Why does yeast make limewater go milky?", "yeast_fermentation_lab"),
    ],
)
def test_a_question_that_names_an_environment_matches_it(question: str, plan_id: str) -> None:
    match = library.match_by_name(question, NAMED)
    assert match is not None and match["plan_id"] == plan_id


@pytest.mark.parametrize("question", ["What is Newton's law?", "How does a spring work?", "What is the speed of light?", "Why is the sky blue?", ""])
def test_a_question_that_names_nothing_in_particular_matches_nothing(question: str) -> None:
    assert library.match_by_name(question, NAMED) is None


def test_a_question_the_topic_head_cannot_place_but_that_names_an_environment_is_answered_from_the_library(
    seeded_db: Path, tmp_path: Path, kit_dist: Path
) -> None:
    deps, provider = seeded_deps(seeded_db, tmp_path, kit_dist)
    events = collect("How do I revise Hooke's law?", deps)
    assert provider.calls == [], "the library answers a named Environment with no model call"
    block = next(e for e in events if e.type == "environment").block
    assert block.lane == "instantiate" and block.id.startswith("hookes_amali-")
    hit = next(r for r in trace_records(deps) if r["layer"] == "library")
    assert hit["status"] == "hit" and hit["detail"]["kind"] in ("name", "topic")


def test_an_empty_library_names_nothing() -> None:
    assert library.match_by_name("How do I revise Hooke's law?", []) is None

