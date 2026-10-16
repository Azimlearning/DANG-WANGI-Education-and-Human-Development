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
from api.llm.pricing import cost_usd  # noqa: E402
from api.pipeline import prompts  # noqa: E402
from api.pipeline.fill import contract_for  # noqa: E402
from eval.golden.run import load as load_golden  # noqa: E402

REPORT = REPO / "refdocs" / "evidence" / "2026-10-16-p3-cost-projection.md"
KIT = REPO / "packages" / "kit" / "dist"
PLANS = REPO / "data" / "plans"

# ── assumptions (each is printed in the report) ──────────────────────────────────────────────────────────────────────────
TOKEN_RATIO_LOW, TOKEN_RATIO_HIGH = 4, 3  # characters per token: the usual figure, and the ledger's conservative one
OUT_PLAN_SCALE = (0.8, 1.6)  # model plan output vs the golden plan's JSON length
OUT_EXPLAIN = (150, 450)
OUT_ROUTE = (40, 100)
OUT_FILL = (60, 220)
CACHE_READ_FRACTION = 0.10  # share of the normal input price paid for a cached stable prefix
P_ROUTE_FALLBACK = (
    0.9  # measured: the pattern and complexity heads clear their gates for only about a third of questions
)
P_PLAN_RETRY = (0.0, 0.4)
P_FILL = (0.0, 1.0)
SMOKE_QUESTIONS = 9  # three per Physics Form 5 topic
SMOKE_RETRIES = 1.5  # multiplier on the high case for a first run: the planner has never been tried


def tokens(chars: int, ratio: int) -> int:
    return -(-chars // ratio)


def cost(tier: str, tin: int, tout: int, cached_in: int = 0) -> float:
    model = ANTHROPIC_MODELS[tier]  # type: ignore[index]
    full = cost_usd("anthropic", model, tin - cached_in, tout)
    cached = cost_usd("anthropic", model, cached_in, 0) * CACHE_READ_FRACTION
    return full + cached


def per_question(manifest: kitmanifest.Manifest, question: dict, plan_json_chars: int) -> dict:
    q = question["question"]
    route_summary = f"topic={question['expect_topic']}; domain=physics; pattern=simulation; complexity=2"
    plan_req = prompts.plan_request(q, route_summary, "virtual_experiment", manifest)
    explain_req = prompts.explain_request(q, route_summary)
    fill_req = prompts.fill_request("extra", "One more sentence.", contract_for("extra"), ("env", "c_load", "m_spring"))
    route_chars = 2600 + len(
        q
    )  # the router-fallback prompt is a fixed pack plus the topic list; measured by hand once, see the report
    parts = {
        "plan": (plan_req, len(plan_req.system or ""), plan_json_chars),
        "explain": (explain_req, len(explain_req.system or ""), None),
        "fill": (fill_req, len(fill_req.system or ""), None),
    }
    out = {}
    for name, (req, sys_chars, plan_chars) in parts.items():
        chars_in = len(req.prompt) + sys_chars
        out[name] = {"chars_in": chars_in, "stable_chars": sys_chars, "plan_chars": plan_chars}
    out["route"] = {"chars_in": route_chars, "stable_chars": 2200, "plan_chars": None}
    return out


def scenario(per: dict, which: str) -> float:
    low = which == "low"
    ratio = TOKEN_RATIO_LOW if low else TOKEN_RATIO_HIGH

    def part(name: str, tier: str, out_tokens: int, calls: float, cached: bool) -> float:
        info = per[name]
        tin = tokens(info["chars_in"], ratio)
        stable = tokens(info["stable_chars"], ratio) if cached else 0
        return calls * cost(tier, tin, out_tokens, stable)

    plan_out = int(tokens(per["plan"]["plan_chars"], TOKEN_RATIO_LOW) * OUT_PLAN_SCALE[0 if low else 1])
    total = part("explain", "standard", OUT_EXPLAIN[0 if low else 1], 1, low)
    total += part("plan", "standard", plan_out, 1 + P_PLAN_RETRY[0 if low else 1], low)
    total += part("route", "light", OUT_ROUTE[0 if low else 1], P_ROUTE_FALLBACK, low)
    total += part("fill", "light", OUT_FILL[0 if low else 1], P_FILL[0 if low else 1], low)
    return total


def build() -> str:
    version = latest_version(KIT)
    manifest = kitmanifest.load(KIT, version)
    golden = load_golden()
    plan_chars = {json.loads(p.read_text())["topic"]: len(p.read_text()) for p in sorted(PLANS.glob("*.json"))}
    rows = []
    for q in golden:
        per = per_question(manifest, q, plan_chars[q["expect_topic"]])
        rows.append((q["id"], scenario(per, "low"), scenario(per, "high")))
    lows = [r[1] for r in rows]
    highs = [r[2] for r in rows]
    mean_low, mean_high = sum(lows) / len(lows), sum(highs) / len(highs)
    smoke_low = mean_low * SMOKE_QUESTIONS
    smoke_high = mean_high * SMOKE_QUESTIONS * SMOKE_RETRIES
    sample = prompts.plan_request("sample", "topic=x", "virtual_experiment", manifest)
    return f"""# Cost projection for the first vertical (Physics Form 5), P3

> Generated by `uv run python eval/cost/project.py` (do not edit by hand; a test fails if it is stale). **No model call was made to produce this.**
> Per CLAUDE.md rule 7 the owner must confirm an amount before any paid run. This note proposes one.

## Projected cost per Environment

| Case | USD per Environment | What it assumes |
|---|---|---|
| Low | **{mean_low:.4f}** | no plan retry, no slot fill, the stable prefix cached, 4 characters per token, short outputs |
| High | **{mean_high:.4f}** | one plan retry 40 percent of the time, a slot fill, no caching, 3 characters per token, long outputs |

Mean over the {len(golden)} golden questions, from the real prompts the pipeline builds. For comparison, Synapse v3 spent about $0.19 per whole-page generation (an unverified figure from v3's notes, A-4).

## Proposed first paid run (the amount to confirm)

- {SMOKE_QUESTIONS} questions, three per Physics Form 5 topic (spring, circuit, liquid pressure), live mode, the verifier unchanged.
- Projected: **${smoke_low:.2f} to ${smoke_high:.2f}**. Suggested cap `LLM_MONTHLY_CAP_USD`: **$5**, which is more than 20 times the high case and still small.
- What it would measure that nothing else can: the rate of valid plans (the biggest unknown), tokens per layer, the real retry rate, the cache hit rate, and whether the fail-check registry's hints fix a bad plan.
- It would not measure: correctness against a textbook (the corpus is not loaded; labels stay `model-checked`, D-21).
- **Waiting for the owner's reply with an amount. Nothing is sent until then.**

## Size of the real prompts (characters, rounded)

- Plan request (virtual experiment): about {len(sample.system or "") + len(sample.prompt)} characters, of which {len(sample.system or "")} are the stable cached prefix.
- Explain, fill and route-fallback requests are small (a few hundred to about 3,000 characters).

## Assumptions (each can be wrong; the first paid run replaces them with measurements)

1. Prices are `api/llm/pricing.py`'s, marked ASSUMED (unchecked against the provider's pricing page). Models: plan and explain on the standard tier, route fallback and fill on the light tier.
2. Tokens: {TOKEN_RATIO_LOW} characters per token (low) or {TOKEN_RATIO_HIGH} (high). A provider's tokenizer differs.
3. Output sizes: plan = the golden plan's JSON length times {OUT_PLAN_SCALE[0]} (low) or {OUT_PLAN_SCALE[1]} (high); explain {OUT_EXPLAIN[0]} to {OUT_EXPLAIN[1]} tokens; route fallback {OUT_ROUTE[0]} to {OUT_ROUTE[1]}; fill {OUT_FILL[0]} to {OUT_FILL[1]}.
4. The router fallback is called for {int(P_ROUTE_FALLBACK * 100)} percent of questions (the pattern and complexity heads clear their gates for about a third of questions, and a local `none` topic always goes to the fallback).
5. Plan retry rate {int(P_PLAN_RETRY[0] * 100)} to {int(P_PLAN_RETRY[1] * 100)} percent. Nothing here can measure it: fakes always return a valid plan.
6. Prompt caching pays {int(CACHE_READ_FRACTION * 100)} percent of the input price for the stable prefix in the low case and is not used in the high case. Whether the provider's cache applies to this request shape is unverified (A-4).
7. The L4 model check, the repair prompt beyond one retry and the Free lane are not included (not built).
8. Verification costs no model call.

## Per-question range

| Question | Low USD | High USD |
|---|---|---|
{chr(10).join(f"| {i} | {lo:.4f} | {hi:.4f} |" for i, lo, hi in rows)}
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
