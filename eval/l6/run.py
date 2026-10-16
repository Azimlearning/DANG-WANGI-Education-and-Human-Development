"""Run every planted mutation through the real verifier and write the L6 baseline report.

    uv run python eval/l6/run.py            # prints the table and rewrites the report
    uv run python eval/l6/run.py --only kit  # a subset by id prefix

Free to run (no model calls). It drives a real browser, so it takes about a minute and a half.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.kit import latest_version  # noqa: E402
from api.schema.generated import Citation  # noqa: E402
from api.verify.mint import VerificationFailed, verify_environment  # noqa: E402
from eval.l6.mutations import MUTATIONS, Mutation  # noqa: E402

FIXTURES = REPO / "data" / "fixtures" / "envs"
KIT_DIST = REPO / "packages" / "kit" / "dist"
REPORT = REPO / "refdocs" / "evidence" / "2026-10-16-p1-l6-baseline.md"
ORIGIN = "http://localhost:3000"

LAYER_OF_RULE = {
    # L1: provenance
    "ungrounded_readout": "L1 provenance",
    "unaudited_arithmetic": "L1 provenance",
    "unknown_model": "L1 provenance",
    "readout_mismatch": "L1 provenance",
    "owned_changed": "L1 provenance",
    "unowned_number": "L1 provenance",
    "unowned_attribute_number": "L1 provenance",
    "shadow_root": "L1 provenance",
    "bad_unit_factor": "L1 provenance",
    "unbacked_copy_number": "L1 provenance",
    "kit_not_intact": "L1 provenance",
    "kit_missing": "L1 provenance",
    "plan_mismatch": "L1 provenance (plan)",
    "plan_missing": "L1 provenance (plan)",
    "forbidden_markup": "L1 provenance",
    "wrong_input_unit": "L1 provenance",
    "constant_readout": "L1 provenance",
    "control_mismatch": "L1 provenance",
    "malformed_audit": "L1 provenance",
    "unregistered_readout": "L1 provenance",
    "runtime_violation": "runtime self-check",
    "forged_action": "L1 provenance",
    "wrong_unit": "L1 provenance",
    # L3: reference
    "numeric_mismatch": "L3 reference",
    "reference_error": "L3 reference",
    "non_finite_readout": "L3 reference",
    # L2: behaviour
    "dead_control": "L2 behaviour",
    "unstable_readout": "L2 behaviour",
    "no_controls": "L2 behaviour",
    "undeclared_control": "L2 behaviour",
    "duplicate_control": "L2 behaviour",
    # runtime and structure
    "navigation": "runtime",
    "harness_error": "runtime",
    "errors": "runtime",
    "blocked_request": "runtime",
    "ready": "runtime",
    "a11y": "accessibility",
    "touch_target": "accessibility",
    "horizontal_overflow": "layout",
}


def layer_of(stage: str, rule: str) -> str:
    if stage in ("scan", "postprocess", "kit"):
        return "L0 scan"
    return LAYER_OF_RULE.get(rule, f"other ({rule})")


@dataclass
class Outcome:
    m: Mutation
    refused: bool
    stage: str = ""
    rule: str = ""
    reason: str = ""
    neutralised: bool = (
        False  # for expect == "neutralise": the minted HTML carries exactly our CSP, first, and nothing else
    )

    @property
    def layer(self) -> str:
        return layer_of(self.stage, self.rule) if self.refused else "none"

    @property
    def status(self) -> str:
        if self.m.expect == "accept":
            return "ok" if not self.refused else "FALSE POSITIVE"
        if self.m.expect == "neutralise":
            return "refused" if self.refused else ("neutralised" if self.neutralised else "NOT NEUTRALISED")
        if self.refused:
            return "caught"
        return "known miss" if self.m.known_miss else "MISSED"


def _plan(base: str) -> dict:
    return json.loads((FIXTURES / base.replace(".html", ".plan.json")).read_text(encoding="utf-8"))


def run_one(m: Mutation, work: Path) -> Outcome:
    plan = _plan(m.base)
    html = m.edit((FIXTURES / m.base).read_text(encoding="utf-8"))
    version = latest_version(KIT_DIST)
    dist = KIT_DIST
    if m.kit_edit:
        dist = work / m.id
        shutil.copytree(KIT_DIST / version, dist / version)
        core = dist / version / "core.js"
        text = core.read_text(encoding="utf-8")
        patched, count = re.subn(m.kit_edit[0], m.kit_edit[1], text, count=1)
        if count != 1:
            raise AssertionError(f"{m.id}: Kit anchor not found: {m.kit_edit[0]!r}")
        core.write_text(patched, encoding="utf-8")
    try:
        minted = verify_environment(
            slug=plan["id"],
            title=plan["title"],
            raw_html=html,
            lane="instantiate",
            label="model-checked",
            kit_version=version,
            citations=[Citation(source="UNVERIFIED (L6 mutation run)", page=None, quote=None, verified=False)],
            plan_summary="L6 mutation",
            public_origin=ORIGIN,
            kit_dist=dist,
            interaction_seconds=1.0,
            plan_models=plan.get("models"),
        )
    except VerificationFailed as e:
        return Outcome(m, True, e.stage, e.rule, str(e)[:160])
    if m.expect == "neutralise":
        from api import postprocess

        html_out = minted.html
        ours = html_out.lower().count("content-security-policy") == 1 and postprocess.csp_is_first(html_out, ORIGIN)
        return Outcome(m, False, neutralised=ours and "default-src *" not in html_out)
    return Outcome(m, False)


def table(outcomes: list[Outcome]) -> str:
    rows = ["| Mutation | Class | What was planted | Result | Refused by | Rule |", "|---|---|---|---|---|---|"]
    for o in outcomes:
        rows.append(f"| `{o.m.id}` | {o.m.klass} | {o.m.what} | {o.status} | {o.layer} | {o.rule or 'none'} |")
    return "\n".join(rows)


def summarise(outcomes: list[Outcome]) -> dict:
    defects = [o for o in outcomes if o.m.expect == "refuse"]
    neutral = [o for o in outcomes if o.m.expect == "accept"]
    neutralised = [o for o in outcomes if o.m.expect == "neutralise"]
    by_class: dict[str, list[Outcome]] = defaultdict(list)
    for o in defects:
        by_class[o.m.klass].append(o)
    return {
        "defects": len(defects),
        "caught": sum(o.refused for o in defects),
        "known_misses": [o.m.id for o in defects if not o.refused and o.m.known_miss],
        "surprise_misses": [o.m.id for o in defects if not o.refused and not o.m.known_miss],
        "neutral": len(neutral),
        "neutralise_total": len(neutralised),
        "not_neutralised": [o.m.id for o in neutralised if not o.refused and not o.neutralised],
        "false_positives": [o.m.id for o in neutral if o.refused],
        "by_class": {k: (sum(o.refused for o in v), len(v)) for k, v in by_class.items()},
        "by_layer": Counter(o.layer for o in defects if o.refused),
    }


def write_report(outcomes: list[Outcome]) -> None:
    s = summarise(outcomes)
    layer_rows = "\n".join(f"| {k} | {v} |" for k, v in sorted(s["by_layer"].items(), key=lambda kv: -kv[1]))
    class_rows = "\n".join(f"| {k} | {c} of {n} |" for k, (c, n) in sorted(s["by_class"].items()))
    notes = "\n".join(f"- `{o.m.id}`: {o.m.note}" for o in outcomes if o.m.known_miss and o.m.note)
    text = f"""# L6 baseline: planted defects through the real verifier

> Generated by `uv run python eval/l6/run.py` (do not edit by hand). Kit {latest_version(KIT_DIST)}. Fakes only, no model calls.
> **What this is:** a measured detection rate on defects someone thought of. **What it is not:** the rate on defects in general. The
> planted classes are listed below; the classes not tried are listed after them. Both lists are part of the result.

## Result

- Defects planted: **{s["defects"]}**. Refused: **{s["caught"]}** ({100 * s["caught"] / s["defects"]:.0f} percent of the planted set).
- Known misses (defects we believe the verifier cannot see, kept on the record): **{len(s["known_misses"])}**: {", ".join(f"`{x}`" for x in s["known_misses"]) or "none"}.
- Surprise misses (a planted defect nobody expected to pass): **{len(s["surprise_misses"])}**: {", ".join(f"`{x}`" for x in s["surprise_misses"]) or "none"}.
- Neutral controls refused (false positives): **{len(s["false_positives"])} of {s["neutral"]}**: {", ".join(f"`{x}`" for x in s["false_positives"]) or "none"}.

- Defects the post-processor is meant to neutralise rather than refuse (a model-written CSP, a comment hiding the head): **{s["neutralise_total"] - len(s["not_neutralised"])} of {s["neutralise_total"]}** ended with exactly our policy, first, and no other. Not neutralised: {", ".join(f"`{x}`" for x in s["not_neutralised"]) or "none"}.

Detection among the defects the design claims to cover (planted defects minus the known misses): {s["caught"]} of {s["defects"] - len(s["known_misses"])}.

**Read the rate with this in mind:** the set was grown while the verifier was built, and several holes it found (attribute numbers, shadow
roots, late insertion, a forged readout at load, a wrong unit label, a wrong conversion factor) were closed because a mutation exposed
them. So this is a regression baseline that gets harder as it grows, not an unbiased estimate of detection on unseen defects.

## By class

| Class | Refused |
|---|---|
{class_rows}

## Which layer refused first

The harness reports the first failed rule, so this is "first to refuse", not "every layer that would have refused".

| Layer | Defects refused first by it |
|---|---|
{layer_rows}

## Every mutation

{table(outcomes)}

## Known misses, and why

{notes}

## Classes not tried

- Conditional or time-triggered behaviour the harness never reaches (a branch taken only on a touch screen, or after a minute). The
  verifier cannot see it. The Kit's runtime self-check catches a forged readout in the student's browser and the host closes the
  Environment (D-24); isolation (A-10) would not help with this class, only with network exfiltration.
- Bugs in the Kit that are wrong in the same way in its own reference and in the Python reference (they share an author).
- Defects in prose that contain no numbers (see the known misses), and defects in the choice of model for the question.
- Accessibility defects beyond the static fence (focus order, screen-reader reading order).
- Resource exhaustion (an endless loop, a huge allocation) beyond the render timeout.
- Multi-step attacks that depend on the host (the bridge) rather than the page.
- Anything the model could write that uses a browser feature none of us listed.

## How to read the numbers

A high rate here means the listed holes are closed. It does not mean generated Environments are correct. The two things that bound
trust are the textbook grounding (P2) and a person's review, not this table.
"""
    REPORT.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="run only mutations whose id starts with this prefix")
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()
    chosen = [m for m in MUTATIONS if m.id.startswith(args.only)]
    outcomes: list[Outcome] = []
    with tempfile.TemporaryDirectory() as tmp:
        for m in chosen:
            o = run_one(m, Path(tmp))
            outcomes.append(o)
            print(f"{o.status:15} {m.id:34} {o.layer:24} {o.rule}", flush=True)
    s = summarise(outcomes)
    print(
        f"\nrefused {s['caught']} of {s['defects']} planted defects; false positives {len(s['false_positives'])} of {s['neutral']}"
    )
    print("surprise misses:", s["surprise_misses"] or "none")
    if not args.no_report and not args.only:
        write_report(outcomes)
        print(f"wrote {REPORT.relative_to(REPO)}")
    return 1 if s["surprise_misses"] or s["false_positives"] or s["not_neutralised"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
