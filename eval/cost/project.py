"""Project the cost of one Environment, as a range with every assumption named. Makes NO model call and needs no key.

    uv run python eval/cost/project.py            # writes refdocs/evidence/2026-10-16-p3-cost-projection.md
    uv run python eval/cost/project.py --check    # exit 1 if the report is stale

The input sizes are the REAL prompts the pipeline builds for the golden questions (api/pipeline/prompts.py). Everything else is an assumption, listed
in the report. Prices are api/llm/pricing.py's, which are themselves ASSUMED (unchecked against the provider's page). Rule 7: a paid run states a
projected amount first and waits for the owner. This file produces the amount; it does not spend it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api import kitmanifest  # noqa: E402
from api.kit import latest_version  # noqa: E402
from api.llm.models import ANTHROPIC_MODELS  # noqa: E402
from api.llm.pricing import cost_usd, estimate_call_cost  # noqa: E402
from api.pipeline import prompts  # noqa: E402
from api.pipeline.fill import contract_for  # noqa: E402
from api.pipeline.plan import parse as parse_plan  # noqa: E402
from api.pipeline.run import MAX_LLM_CALLS  # noqa: E402
from api.routing import fallback as route_fallback  # noqa: E402
from api.routing.router import topic_names  # noqa: E402
from eval.golden.run import load as load_golden  # noqa: E402

REPORT = REPO / "refdocs" / "evidence" / "2026-10-16-p3-cost-projection.md"
KIT = REPO / "packages" / "kit" / "dist"
PLANS = REPO / "data" / "plans"
FREE_SAMPLE = REPO / "data" / "fixtures" / "envs" / "free-pressure.html"

# ── assumptions (each is printed in the report) ──────────────────────────────────────────────────────────────────────────
TOKEN_RATIO_LOW, TOKEN_RATIO_HIGH = 4, 3  # characters per token: the usual figure, and the ledger's conservative one
OUT_PLAN_SCALE = (0.8, 1.6)  # model plan output vs the golden plan's JSON length
OUT_EXPLAIN = (150, 450)
OUT_ROUTE = (40, 100)
OUT_FILL = (60, 220)
OUT_WORDING = (30, 120)  # the judge's JSON verdict: {"ok": true, "issues": []} up to a few short issues
OUT_FREE = (2500, 6000)  # a whole Free page; 6,000 is the request's max_tokens (prompts.FREE_MAX_TOKENS), 2,500 a plausible short page
OUT_FREE_WORDING = (30, 150)
P_ROUTE_FALLBACK = (
    0.9  # measured: the pattern and complexity heads clear their gates for only about a third of questions
)
P_PLAN_RETRY = (0.0, 0.4)
P_PLAN_RETRY_PESSIMISTIC = 1.0  # Arcana v2's live generator was accepted on 2 of 8 first attempts (refdocs/synapse-v4-sources.md), so 40 percent is not an upper bound
CANARY_QUESTIONS = 1
P_FILL = (0.0, 1.0)
SMOKE_QUESTIONS = 9  # three per Physics Form 5 topic
SMOKE_RETRIES = 1.5  # multiplier on the high case for a first run: the planner has never been tried


def tokens(chars: int, ratio: int) -> int:
    return -(-chars // ratio)


def cost(tier: str, tin: int, tout: int) -> float:
    model = ANTHROPIC_MODELS[tier]  # type: ignore[index]
    return cost_usd("anthropic", model, tin, tout)


def per_question(manifest: kitmanifest.Manifest, question: dict, plan_json_chars: int, golden_plan_text: str) -> dict:
    q = question["question"]
    route_summary = f"topic={question['expect_topic']}; domain=physics; pattern=simulation; complexity=2"
    plan_req = prompts.plan_request(q, route_summary, "virtual_experiment", manifest, topic=question["expect_topic"])  # the real pipeline passes the topic
    explain_req = prompts.explain_request(q, route_summary)
    fill_req = prompts.fill_request("extra", "One more sentence.", contract_for("extra"), ("env", "c_load", "m_spring"))
    names = topic_names()
    route_req = route_fallback.build_request(
        q,
        {
            "topic": [*names, "none"],
            "domain": ["biology", "chemistry", "physics"],
            "pattern": ["simulation", "virtual_experiment"],
            "complexity": ["1", "2", "3"],
        },
        names,
    )
    # The new calls (D-41). The judge reads the golden Plan's words; the Free calls use the hand-written sample page as a stand-in for a model's page (a real
    # one is longer, which is why its output is an assumption and not read from here).
    wording_req = prompts.wording_request(parse_plan(golden_plan_text))
    free_req = prompts.free_request(q, route_summary)
    free_wording_req = prompts.free_wording_request(q, FREE_SAMPLE.read_text(encoding="utf-8"))
    tiers = {"plan": "standard", "explain": "standard", "fill": "light", "route": "light", "wording": "light", "free": "standard", "free_wording": "standard"}
    reqs = {"plan": plan_req, "explain": explain_req, "fill": fill_req, "route": route_req, "wording": wording_req, "free": free_req, "free_wording": free_wording_req}
    out: dict = {}
    for name, req in reqs.items():
        sys_chars = len(req.system or "")
        out[name] = {
            "chars_in": len(req.prompt) + sys_chars,
            "stable_chars": sys_chars,
            "plan_chars": plan_json_chars if name == "plan" else None,
            # What the ledger itself would reserve before sending: the hard bound, with every reply running to max_tokens.
            "reserve": estimate_call_cost("anthropic", ANTHROPIC_MODELS[tiers[name]], req),  # type: ignore[index]
        }
    return out


def worst_case_reserve(per: dict) -> float:
    """The ledger's own worst case for one Compose request with the wording check on: the 8-call path route, explain, plan, wording, plan retry, wording,
    fill, fill retry."""
    r = {k: per[k]["reserve"] for k in ("route", "explain", "plan", "fill", "wording")}
    return r["route"] + r["explain"] + 2 * r["plan"] + 2 * r["wording"] + 2 * r["fill"]


def worst_case_free_reserve(per: dict) -> float:
    """The worst case with the Free lane on: route, explain, two plans each read by the judge, then one Free page and its reading (also 8 calls)."""
    r = {k: per[k]["reserve"] for k in ("route", "explain", "plan", "wording", "free", "free_wording")}
    return r["route"] + r["explain"] + 2 * r["plan"] + 2 * r["wording"] + r["free"] + r["free_wording"]


def free_extra(per: dict, which: str) -> float:
    """What a Free page adds when it fires, on top of the failed Compose attempts: the page and its reading."""
    low = which == "low"
    ratio = TOKEN_RATIO_LOW if low else TOKEN_RATIO_HIGH
    i = 0 if low else 1
    return cost("standard", tokens(per["free"]["chars_in"], ratio), OUT_FREE[i]) + cost(
        "standard", tokens(per["free_wording"]["chars_in"], ratio), OUT_FREE_WORDING[i]
    )


def scenario(per: dict, which: str) -> float:
    low = which == "low"
    ratio = TOKEN_RATIO_LOW if low else TOKEN_RATIO_HIGH

    def part(name: str, tier: str, out_tokens: int, calls: float) -> float:
        # Prompt caching is off (the ledger cannot price cache writes), so every input token is paid at the full rate in every case.
        return calls * cost(tier, tokens(per[name]["chars_in"], ratio), out_tokens)

    plan_out = int(tokens(per["plan"]["plan_chars"], TOKEN_RATIO_LOW) * OUT_PLAN_SCALE[0 if low else 1])
    total = part("explain", "standard", OUT_EXPLAIN[0 if low else 1], 1)
    total += part("plan", "standard", plan_out, 1 + P_PLAN_RETRY[0 if low else 1])
    total += part("route", "light", OUT_ROUTE[0 if low else 1], P_ROUTE_FALLBACK)
    total += part("fill", "light", OUT_FILL[0 if low else 1], P_FILL[0 if low else 1])
    total += part("wording", "light", OUT_WORDING[0 if low else 1], 1 + P_PLAN_RETRY[0 if low else 1])  # the judge reads every plan that passes the checks
    return total


def pessimistic(per: dict) -> float:
    """The high case with every plan retried once (retry rate 100 percent)."""
    saved = P_PLAN_RETRY
    try:
        globals()["P_PLAN_RETRY"] = (0.0, P_PLAN_RETRY_PESSIMISTIC)
        return scenario(per, "high")
    finally:
        globals()["P_PLAN_RETRY"] = saved


def build() -> str:
    version = latest_version(KIT)
    manifest = kitmanifest.load(KIT, version)
    golden = load_golden()
    plan_chars = {json.loads(p.read_text())["topic"]: len(p.read_text()) for p in sorted(PLANS.glob("*.json"))}
    plan_text = {json.loads(p.read_text())["topic"]: p.read_text() for p in sorted(PLANS.glob("*.json"))}
    rows = []
    worst = worst_free = 0.0
    free_lows: list[float] = []
    free_highs: list[float] = []
    for q in golden:
        per = per_question(manifest, q, plan_chars[q["expect_topic"]], plan_text[q["expect_topic"]])
        free_lows.append(free_extra(per, "low"))
        free_highs.append(free_extra(per, "high"))
        worst_free = max(worst_free, worst_case_free_reserve(per))
        rows.append((q["id"], scenario(per, "low"), scenario(per, "high"), pessimistic(per)))
        worst = max(worst, worst_case_reserve(per))
    n = len(rows)
    free_low, free_high = sum(free_lows) / n, sum(free_highs) / n
    mean_low, mean_high, mean_pess = (sum(r[k] for r in rows) / n for k in (1, 2, 3))
    smoke_low = mean_low * SMOKE_QUESTIONS
    smoke_pess = mean_pess * SMOKE_QUESTIONS
    smoke_worst = worst * SMOKE_QUESTIONS
    canary_worst = worst * CANARY_QUESTIONS
    sample = prompts.plan_request("sample", "topic=x", "virtual_experiment", manifest)
    return f"""# Cost projection for the first vertical (Physics Form 5), P3

> Generated by `uv run python eval/cost/project.py` (do not edit by hand; a test fails if it is stale). **No model call was made to produce this.**
> Per CLAUDE.md rule 7 the owner must confirm an amount before any paid run. This note proposes one. A cost-auditor review of the seam is recorded in the changelog.

## Projected cost per Environment

| Case | USD per Environment | What it assumes |
|---|---|---|
| Low | **{mean_low:.4f}** | no plan retry, no slot fill, 4 characters per token, short outputs (no caching in any case) |
| High | **{mean_high:.4f}** | one plan retry 40 percent of the time, a slot fill, no caching, 3 characters per token, long outputs |
| Pessimistic | **{mean_pess:.4f}** | the high case with every plan retried once (retry rate {int(P_PLAN_RETRY_PESSIMISTIC * 100)} percent) |
| Hard bound | **{worst:.4f}** | what the ledger itself would reserve for the worst allowed Compose path of {MAX_LLM_CALLS} calls (route, explain, plan, wording check, plan retry, wording check, fill, fill retry), every reply running to its max_tokens |
| Free lane, extra when it fires | **{free_low:.4f}** to **{free_high:.4f}** | the Free page and its reading ({OUT_FREE[0]} to {OUT_FREE[1]} output tokens for the page), on top of the failed Compose attempts. Off by default; unmeasured |
| Hard bound with the Free lane on | **{worst_free:.4f}** | route, explain, two plans each read by the judge, then one Free page and its reading ({MAX_LLM_CALLS} calls), every reply running to its max_tokens |

Mean over the {n} golden questions (each hard bound is the largest over them; the wording check is counted because live mode turns it on), from the real prompts the pipeline builds. For comparison, Synapse v3 spent about $0.19 per whole-page generation (an unverified figure from v3's notes, A-4).

## Proposed first paid run (the amounts to confirm)

1. **A canary of {CANARY_QUESTIONS} question** first: up to **${canary_worst:.4f}** (hard bound), expected about ${mean_low:.3f} to ${mean_high:.3f}. It checks model ids, token counts and error handling for almost nothing.
2. **Then {SMOKE_QUESTIONS} questions**, three per Physics Form 5 topic (spring, circuit, liquid pressure): projected **${smoke_low:.2f} to ${smoke_pess:.2f}**, hard bound **${smoke_worst:.2f}**.
3. **Suggested `LLM_MONTHLY_CAP_USD`: $1.00** for both together. The cap is the last line of defence, so it is set close to the hard bound, not far above it. A second run in the same month adds to the same cap.
- What it would measure that nothing else can: the rate of valid plans (the biggest unknown), tokens per layer, the real retry rate, the real characters per token and any hidden thinking tokens, and whether the fail-check registry's hints fix a bad plan.
- It would not measure: whether the content is right. That is checked by reading the textbook pages against each Plan (Step 2, D-36), and a model-written Plan can only earn `kit-verified` by naming citation ids that exist and support it. A teacher's judgement is not measured at all.
- **The live provider is wired (D-34) and has only been run against a mock transport. Nothing is sent until the owner replies with an amount; the seam's prerequisites are listed below.**

## What must exist before the first live call (from the cost audit)

- Done: live mode refuses to build without a key, a positive cap and an absolute ledger path; a provider failure that retrying cannot fix (balance, key, bad request) stops the run and says it is not the cap; timed-out and cancelled calls are booked at their input cost, not zero; `LLMService.ensure_budget` refuses a run whose worst case does not fit; tests no longer inherit a shell's `SYNAPSE_LLM_MODE`.
- Done in the provider class (D-34, re-checked against the provider's pages on 2026-10-18): plain httpx with no retries and a 90 s timeout; usage mapped including cache tokens (caching is off and no saving is assumed); explicit prices for the three tier models; a reply that was billed and then rejected (cut off at max_tokens, empty, refused) is booked at its real tokens, so the cap cannot be under-counted.
- To do in the live run script (`eval/golden/run.py --live`, not yet built): print the ledger path and the month-to-date total, call `ensure_budget`, take the ledger from settings (never a temporary folder), print this projection, refuse without `LLM_MONTHLY_CAP_USD`, and require a typed confirmation.

## Size of the real prompts (characters, rounded)

- Plan request (virtual experiment): about {len(sample.system or "") + len(sample.prompt)} characters, of which {len(sample.system or "")} are the stable prefix (sent in full every time: caching is off).
- The router-fallback request is built by the real builder, with the full topic list.

## Assumptions (each can be wrong; the first paid run replaces them with measurements)

1. Prices are `api/llm/pricing.py`'s, checked against the provider's models and pricing pages on 2026-10-18 (Opus 5.5 $4 and $20, Sonnet 5.5 $2 and $10, Haiku 5.5 $0.10 and $0.50 per million tokens). Models: plan and explain on the standard tier, route fallback and fill on the light tier.
2. Tokens: {TOKEN_RATIO_LOW} characters per token (low) or {TOKEN_RATIO_HIGH} (high). A provider's tokenizer differs.
3. Output sizes: plan = the golden plan's JSON length times {OUT_PLAN_SCALE[0]} (low) or {OUT_PLAN_SCALE[1]} (high); explain {OUT_EXPLAIN[0]} to {OUT_EXPLAIN[1]} tokens; route fallback {OUT_ROUTE[0]} to {OUT_ROUTE[1]}; fill {OUT_FILL[0]} to {OUT_FILL[1]}. The hard bound assumes every reply runs to its max_tokens.
4. The router fallback is called for {int(P_ROUTE_FALLBACK * 100)} percent of questions (the pattern and complexity heads clear their gates for about a third of questions, and a local `none` topic always goes to the fallback).
5. Plan retry rate {int(P_PLAN_RETRY[0] * 100)} to {int(P_PLAN_RETRY[1] * 100)} percent in the high case and {int(P_PLAN_RETRY_PESSIMISTIC * 100)} percent in the pessimistic one (Arcana v2 was accepted on 2 of 8 first attempts). Nothing here can measure it: fakes always return a valid plan.
6. Prompt caching is off, so every input token is priced at the full rate in every case. Turning it on needs the ledger to price cache writes and reads, and a measured saving first.
7. The repair prompt beyond one retry is not built. The wording check is included in every case (live mode turns it on) at the light tier. The Free lane is NOT in Low, High or Pessimistic: it fires only when the Kit cannot take a question, how often is unknown, and its page length ({OUT_FREE[0]} to {OUT_FREE[1]} tokens) is a guess. Its cost is shown on its own rows.
8. Verification costs no model call.
9. The Free sample page used for input sizes is a short hand-written fixture; a model's page is longer, so the Free input estimate (the reading of the page) is low. The output bound is exact: the request's max_tokens.

## Per-question range

| Question | Low USD | High USD | Pessimistic USD |
|---|---|---|---|
{chr(10).join(f"| {i} | {lo:.4f} | {hi:.4f} | {pe:.4f} |" for i, lo, hi, pe in rows)}
"""


def main() -> int:
    text = build()
    if "--check" in sys.argv:
        ok = REPORT.exists() and REPORT.read_text(encoding="utf-8") == text
        print("up to date" if ok else "stale")
        return 0 if ok else 1
    REPORT.write_text(text, encoding="utf-8")
    print(text.split("## Proposed first paid run")[0][-700:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
