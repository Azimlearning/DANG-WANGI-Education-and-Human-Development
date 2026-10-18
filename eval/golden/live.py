"""The paid run: the golden questions through the real pipeline with the real provider (CLAUDE.md rule 7, D-08). Reached only through `eval/golden/run.py --live`.

What it does before a single request is sent, every time:
  1. refuses unless `LLM_MONTHLY_CAP_USD` is set (the same check live mode itself makes), and prints the cap, this month's spend and what remains;
  2. prints the projected cost of exactly the questions selected (low, high, and the hard bound the ledger itself would reserve) and refuses a run whose hard
     bound does not fit in what remains of the cap;
  3. waits for the person to TYPE the most they approve spending, in dollars. There is no flag that supplies it. Nothing typed, an amount that is not a
     positive number, an amount above what remains of the cap, or a closed input: nothing is sent.
While it runs it stops starting questions when the approved amount could no longer cover the next one's high-case cost. The monthly cap in the ledger is the
last line of defence either way: a call that would exceed it is refused before it is sent.

It writes what it measured (per question: what was made, the lane and label, the degrade rungs, seconds, the cost, and every model call with its tokens) to
`eval/golden/results/<UTC time>-live.json`, and the pipeline's trace to `<data dir>/traces.jsonl`.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.core.settings import ConfigError, Settings  # noqa: E402
from api.evidence.corpus import Corpus  # noqa: E402
from api.evidence.registry import CitationBook  # noqa: E402
from api.llm.factory import build_ledger, build_llm_service  # noqa: E402
from api.llm.ledger import SpendLedger, engine_for  # noqa: E402
from api.llm.models import ANTHROPIC_MODELS  # noqa: E402
from api.llm.service import LLMService  # noqa: E402
from api.pipeline import run as pipeline  # noqa: E402
from api.verify.store import SqliteEnvironmentStore  # noqa: E402

RESULTS = REPO / "eval" / "golden" / "results"


@dataclass(frozen=True)
class Projection:
    low: float
    high: float
    hard_bound: float
    per_question: dict[str, dict[str, float]]


def project(questions: list[dict]) -> Projection:
    """The cost projection (eval/cost/project.py) for exactly these questions, from the real prompts the pipeline builds."""
    from api import kitmanifest
    from api.kit import latest_version
    from eval.cost import project as cost

    manifest = kitmanifest.load(cost.KIT, latest_version(cost.KIT))
    plan_chars = {json.loads(p.read_text(encoding="utf-8"))["topic"]: len(p.read_text(encoding="utf-8")) for p in sorted(cost.PLANS.glob("*.json"))}
    typical = int(sum(plan_chars.values()) / max(1, len(plan_chars)))
    per_question: dict[str, dict[str, float]] = {}
    for q in questions:
        per = cost.per_question(manifest, q, plan_chars.get(q["expect_topic"], typical))
        per_question[q["id"]] = {
            "low": cost.scenario(per, "low"),
            "high": cost.scenario(per, "high"),
            "hard_bound": cost.worst_case_reserve(per),
        }
    return Projection(
        low=sum(v["low"] for v in per_question.values()),
        high=sum(v["high"] for v in per_question.values()),
        hard_bound=sum(v["hard_bound"] for v in per_question.values()),
        per_question=per_question,
    )


def _trace_of_last_run(path: Path | None) -> list[dict]:
    """The planning and verification records of the question that just ran, from the pipeline's trace file, so a refused plan can be diagnosed from the
    results file alone (which model id the planner invented, which binding was wrong) without paying for another run."""
    if path is None or not path.exists():
        return []
    last = path.read_text(encoding="utf-8").strip().splitlines()[-1]
    keep = ("route", "plan", "plan_checks", "assemble", "ground", "verify", "deliver")
    return [
        {"layer": r["layer"], "status": r["status"], "ms": r["ms"], **{k: v for k, v in r["detail"].items() if k in ("attempt", "codes", "issues", "models", "why", "label", "lane", "problems")}}
        for r in json.loads(last)["records"]
        if r["layer"] in keep
    ]


def parse_amount(text: str) -> float | None:
    """A typed dollar amount ("0.75" or "$0.75"), or None if it is not a positive number."""
    try:
        value = float(text.strip().removeprefix("$"))
    except ValueError:
        return None
    return value if value > 0 and value == value and value != float("inf") else None


def describe(settings: Settings, ledger: SpendLedger, projection: Projection, count: int) -> str:
    spent = ledger.month_total()
    cap = settings.llm_monthly_cap_usd or 0.0
    budget = []
    if settings.llm_total_cap_usd is not None:
        total, left = ledger.all_time_total(), max(settings.llm_total_cap_usd - ledger.all_time_total(), 0.0)
        budget = [f"  budget:    ${settings.llm_total_cap_usd:.2f} for the whole project; ${total:.4f} spent in all; ${left:.4f} remains"]
    return "\n".join(
        [
            "A PAID run with the real provider.",
            f"  models:    plan and explain {ANTHROPIC_MODELS['standard']}, route and fill {ANTHROPIC_MODELS['light']}",
            f"  ledger:    {settings.resolved_ledger_path()}",
            f"  cap:       ${cap:.2f} a month; ${spent:.4f} spent so far; ${cap - spent:.4f} remains",
            *budget,
            f"  questions: {count}",
            f"  projected: ${projection.low:.4f} (low) to ${projection.high:.4f} (high)",
            f"  hard bound: ${projection.hard_bound:.4f}, what the ledger would reserve if every call took its longest path and every reply ran to its limit",
            "  a question is started only while the amount you approve can still cover its high figure; type at least the high figure above",
            "  The projection assumes prices and token ratios; the planner has never been run, so the first real numbers replace it.",
        ]
    )


def confirmed_amount(ask: Callable[[str], str], remaining: float) -> float | None:
    """The amount the person typed, or None (nothing is sent). `ask` is `input` in real use."""
    try:
        answer = ask(f"Type the most you approve spending on this run, in dollars (at most ${remaining:.2f}), or anything else to stop: ")
    except EOFError:
        return None
    amount = parse_amount(answer)
    if amount is None or amount > remaining + 1e-9:
        return None
    return amount


async def run_live(
    settings: Settings,
    llm: LLMService,
    ledger: SpendLedger,
    questions: list[dict],
    projection: Projection,
    approved_usd: float,
    store_path: Path,
    out_dir: Path = RESULTS,
    interaction_seconds: float | None = None,
    use_exemplars: bool = True,
) -> dict:
    book = evidence = None
    if settings.corpus_dir is not None and settings.corpus_dir.is_dir():
        book = CitationBook.load(Corpus.load(settings.corpus_dir), settings.corpus_dir)
        evidence = book.evidence
    store_path.parent.mkdir(parents=True, exist_ok=True)
    deps = pipeline.Deps(
        kit_dist=settings.kit_dist_dir,
        public_origin=settings.public_origin,
        store=SqliteEnvironmentStore(store_path),
        llm=llm,
        trace_path=settings.data_dir / "traces.jsonl",
        interaction_seconds=interaction_seconds or settings.verify_interaction_seconds,
        evidence=evidence,
        use_exemplars=use_exemplars,
        citations=book,
    )
    started_at = datetime.now(UTC)
    start_total = ledger.month_total()
    records: list[dict] = []
    stopped = None
    for q in questions:
        spent = ledger.month_total() - start_total
        if spent + projection.per_question[q["id"]]["high"] > approved_usd:
            stopped = f"stopped before {q['id']}: ${spent:.4f} spent and its high case ${projection.per_question[q['id']]['high']:.4f} would pass the approved ${approved_usd:.2f}"
            break
        rows_before = len(ledger.rows())
        before = ledger.month_total()
        t0 = time.monotonic()
        events = [e async for e in pipeline.run(q["question"], deps)]
        seconds = time.monotonic() - t0
        env = next((e.block for e in events if e.type == "environment"), None)
        errors = [e.error for e in events if e.type == "error"]
        calls = [
            {k: r[k] for k in ("purpose", "model", "tokens_in", "tokens_out", "cost_usd", "status")}
            for r in ledger.rows()[rows_before:]
        ]
        records.append(
            {
                "trace": _trace_of_last_run(deps.trace_path),
                "id": q["id"],
                "question": q["question"],
                "expected_topic": q["expect_topic"],
                "environment": env.title if env else None,
                "lane": env.lane if env else None,
                "label": env.label if env else None,
                "degraded": [e.note for e in events if e.type == "stage" and e.status == "degraded"],
                "errors": [{"code": er.code, "retryable": er.retryable} for er in errors],
                "seconds": round(seconds, 1),
                "cost_usd": round(ledger.month_total() - before, 6),
                "projected_high_usd": round(projection.per_question[q["id"]]["high"], 6),
                "calls": calls,
            }
        )
        print(
            f"  {q['id']}: {'environment ' + str(env.label) if env else 'no environment'}; {len(calls)} calls; ${records[-1]['cost_usd']:.4f}; {seconds:.0f}s"
            + (f"; {records[-1]['degraded']}" if records[-1]["degraded"] else ""),
            flush=True,
        )
        if any(er.code == "provider_unavailable" and not er.retryable for er in errors):
            stopped = f"stopped after {q['id']}: the provider refused (its key, balance or our request) and retrying will not help"
            break
        if any(er.code == "spend_cap_exceeded" for er in errors):
            stopped = f"stopped after {q['id']}: the approved ${approved_usd:.2f} (or the monthly cap) would be passed by the next call"
            break
    result = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "approved_usd": approved_usd,
        "exemplars": use_exemplars,
        "spent_usd": round(ledger.month_total() - start_total, 6),
        "projection": {"low": round(projection.low, 4), "high": round(projection.high, 4), "hard_bound": round(projection.hard_bound, 4)},
        "stopped": stopped,
        "questions": records,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{started_at.strftime('%Y%m%dT%H%M%SZ')}-live.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result["path"] = str(path)
    return result


def main_live(
    questions: list[dict],
    *,
    ask: Callable[[str], str] = input,
    env_file: Path | None = REPO / ".env",
    use_exemplars: bool = True,
) -> int:
    """Exit codes: 0 ran, 1 not approved (nothing sent), 2 not configured (nothing sent)."""
    try:
        settings = Settings(_env_file=env_file).model_copy(update={"synapse_llm_mode": "live"})  # pyright: ignore[reportCallIssue]
        if not settings.data_dir.is_absolute():
            settings = settings.model_copy(update={"data_dir": REPO / settings.data_dir})
        if not settings.kit_dist_dir.is_absolute():
            settings = settings.model_copy(update={"kit_dist_dir": REPO / settings.kit_dist_dir})
        ledger = build_ledger(settings)  # refuses without a key, a positive cap and an absolute ledger path
        llm = build_llm_service(settings, ledger)
    except ConfigError as exc:
        print(f"Not sent. {exc}")
        return 2
    try:
        projection = project(questions)
        print(describe(settings, ledger, projection, len(questions)))
        if not use_exemplars:
            print("  NO exemplar: the planner gets no worked example, so this measures planning from the schema and the Kit alone (prompts are shorter,")
            print("  so the projection above is somewhat high; failures and retries are likelier).")
        remaining = ledger.remaining_usd() or 0.0  # the smaller of the monthly cap and the all-time budget
        if projection.hard_bound > remaining:
            print(f"Not sent. The hard bound ${projection.hard_bound:.2f} does not fit in the ${remaining:.2f} that remains of the cap. Run fewer questions.")
            return 1
        approved = confirmed_amount(ask, remaining)
        if approved is None:
            print("Not approved. Nothing was sent.")
            return 1
        # The amount typed is a ceiling, not just a gate to start: this run's ledger is capped at what was already spent plus the approved amount, so the
        # ledger refuses any call that could pass it (the monthly cap still applies underneath).
        run_cap = min(settings.llm_monthly_cap_usd or 0.0, ledger.month_total() + approved)
        run_ledger = SpendLedger(engine_for(settings.resolved_ledger_path()), run_cap, total_cap_usd=settings.llm_total_cap_usd)
        try:
            llm = build_llm_service(settings.model_copy(update={"llm_monthly_cap_usd": run_cap}), run_ledger)
            # A fresh store each run: a question already in the library is answered without the planner, which would hide what the planner does.
            store_path = settings.data_dir / "store" / f"golden-live-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.db"
            result = asyncio.run(
                run_live(settings, llm, run_ledger, questions, projection, approved, store_path, use_exemplars=use_exemplars)
            )
        finally:
            run_ledger.close()
        made = sum(1 for r in result["questions"] if r["environment"])
        print(f"\n{made} of {len(result['questions'])} questions got an Environment; spent ${result['spent_usd']:.4f} of the approved ${approved:.2f}")
        if result["stopped"]:
            print(result["stopped"])
        print(f"results: {result['path']}")
        return 0
    finally:
        ledger.close()
