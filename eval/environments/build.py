"""Assemble every golden plan, verify it in a real browser, store it, and write the list of Environments the project can make today.

    uv run python eval/environments/build.py            # about a minute; writes refdocs/evidence/2026-10-16-p4-environments.md

Free: no model call, fakes only. Every Environment here goes through plan checks, the deterministic assembler, the full verifier (L0 to L3) and the
gate, exactly as a generated one would.

With the local textbook corpus configured (`CORPUS_DIR`, or `--corpus DIR`) each Plan's `citation_ids` are resolved and re-proved against it by the same
`grounding` the live pipeline uses, so a Plan whose every citation proves is `kit-verified` and any other is `model-checked` (D-21, D-25). Without a corpus
every Environment is `model-checked` with an UNVERIFIED citation, and the committed report is NOT rewritten: it records the corpus-verified state, and a
machine without the textbooks must not overwrite it. The report holds counts and pointer ids, never a quotation (hard constraint 13).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api import kitmanifest  # noqa: E402
from api.core.settings import Settings  # noqa: E402
from api.evidence.corpus import Corpus  # noqa: E402
from api.evidence.registry import CitationBook  # noqa: E402
from api.kit import latest_version  # noqa: E402
from api.pipeline import plan as plan_module  # noqa: E402
from api.pipeline.assemble import assemble  # noqa: E402
from api.pipeline.grounding import grounding  # noqa: E402
from api.pipeline.plan_checks import check  # noqa: E402
from api.verify.gate import deliver  # noqa: E402
from api.verify.mint import verify_environment  # noqa: E402
from api.verify.store import SqliteEnvironmentStore  # noqa: E402

PLANS = REPO / "data" / "plans"
KIT = REPO / "packages" / "kit" / "dist"
REPORT = REPO / "refdocs" / "evidence" / "2026-10-16-p4-environments.md"
ORIGIN = "http://localhost:3000"
SUBJECTS = {"physics": "Physics", "biology": "Biology", "chemistry": "Chemistry"}


def corpus_dir(argument: Path | None) -> Path | None:
    """`--corpus`, else the `CORPUS_DIR` setting (process environment or .env), else None."""
    return argument or Settings(_env_file=REPO / ".env").corpus_dir  # pyright: ignore[reportCallIssue]


def build(corpus_path: Path | None = None) -> list[dict]:
    version = latest_version(KIT)
    manifest = kitmanifest.load(KIT, version)
    book = evidence = None
    if corpus_path is not None:
        book = CitationBook.load(Corpus.load(corpus_path), corpus_path)
        evidence = book.evidence
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        store = SqliteEnvironmentStore(Path(tmp) / "envs.db")
        for path in sorted(PLANS.glob("*.json")):
            plan = plan_module.parse(path.read_text(encoding="utf-8"))
            issues = check(plan, manifest)
            if issues:
                raise SystemExit(f"{path.name}: plan checks refused it: {[i.code for i in issues]}")
            page = assemble(plan, manifest)
            citations, label, why = grounding(book, evidence, plan)
            if plan.citation_ids and book is not None and not why["grounded"]:
                print(f"  {plan.id}: NOT grounded, downgraded: {why.get('problems') or why['why']}")
            env = verify_environment(
                slug=plan.id,
                title=plan.title,
                raw_html=page.html,
                lane="instantiate",
                label=label,  # type: ignore[arg-type]  # "kit-verified" or "model-checked", from `grounding`
                kit_version=version,
                citations=citations,
                plan_summary=plan.goal,
                public_origin=ORIGIN,
                kit_dist=KIT,
                interaction_seconds=1.0,
                plan_models=plan.model_summaries(),
                evidence=evidence,
            )
            store.put_verified(env)
            block = deliver(store, env.env_id, public_origin=ORIGIN, kit_dist=KIT, evidence=evidence)
            subject, form = plan.topic.split("_")[0], plan.topic.split("_")[1].removeprefix("form")
            rows.append(
                {
                    "file": path.name,
                    "subject": subject,
                    "form": form,
                    "topic": plan.topic,
                    "title": plan.title,
                    "pattern": plan.pattern,
                    "models": ", ".join(sorted({m.model for m in plan.models})),
                    "controls": len(plan.controls),
                    "grid_points": block.checked.gridPoints,
                    "reference_cases": block.checked.referenceCases,
                    "lane": block.lane,
                    "label": block.label,
                    "sources": sum(1 for c in block.citations if c.verified),
                    "cites": ", ".join(plan.citation_ids) or "none",
                }
            )
    return rows


def render(rows: list[dict]) -> str:
    by_subject = {s: [r for r in rows if r["subject"] == s] for s in SUBJECTS}
    counts = ", ".join(f"{SUBJECTS[s]} {len(v)}" for s, v in by_subject.items())
    verified = sum(1 for r in rows if r["label"] == "kit-verified")
    lines = [
        "| Subject | Form | Title | Pattern | Science model(s) | Grid points | Reference cases | Lane | Label | Verified citations | Citation ids |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in SUBJECTS:
        for r in by_subject[s]:
            lines.append(
                f"| {SUBJECTS[s]} | {r['form']} | {r['title']} | {r['pattern'].replace('_', ' ')} | {r['models']} | {r['grid_points']} | {r['reference_cases']} | {r['lane']} | {r['label']} | {r['sources']} | {r['cites']} |"
            )
    return f"""# Environments the project can make today (P2 and P4)

> Generated by `uv run python eval/environments/build.py` with the owner's local textbook corpus loaded (do not edit by hand). Kit {latest_version(KIT)}. Fakes only; no model call.
> **{len(rows)} Environments: {counts}. {verified} are `kit-verified`.** Each was assembled from a hand-written Plan by the deterministic assembler, passed the plan checks, and was
> verified in real Chromium (L0 scan, L1 provenance, L2 grid and extremes, L3 independent reference) and delivered through the gate, which re-proved every citation against the corpus.
> A run without the corpus verifies the same Environments as `model-checked` and does not rewrite this file.

{chr(10).join(lines)}

## What this does and does not show

- It shows the machinery works across all three subjects: a new science model plus a Plan becomes a verified, interactive Environment with no
  page-writing by a model. The planner (an LLM) has never been run on these; that is the first paid run's job (see the cost projection).
- `kit-verified` here means every citation on the Plan was found word for word on the stated page of the stated textbook by the corpus (exact after
  normalising case, spacing, hyphenation and quote marks), and the citation was checked to support that Plan's topic or science model. It does NOT mean a
  person has reviewed it, and a quotation proves the words are in the book, not that the Environment's formula, units, scope and numbers match them. The
  assistant read each page against its Plan on 2026-10-18 and logged every correction in the changelog; a teacher has not.
- A Plan with no checked citation, or one whose citation did not prove, carries an UNVERIFIED citation and the label `model-checked`. The citation ids are
  pointers in `data/citations/pointers.json`; the quotations themselves live only beside the local corpus (hard constraint 13).
- The Biology photosynthesis curve is a stylised teaching curve, not data, and says so on the page.
- The experiments are named from the KSSM topic list. The owner's experiment catalogue (`data/experiments/catalogue.json`) should replace or confirm each one.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=None, help="the local corpus folder (default: the CORPUS_DIR setting)")
    args = ap.parse_args(argv)
    path = corpus_dir(args.corpus)
    rows = build(path)
    verified = sum(1 for r in rows if r["label"] == "kit-verified")
    if path is None:
        print(f"{len(rows)} Environments verified and delivered as model-checked (no corpus); {REPORT.relative_to(REPO)} NOT rewritten")
        return 0
    REPORT.write_text(render(rows), encoding="utf-8")
    print(f"{len(rows)} Environments verified and delivered, {verified} kit-verified; wrote {REPORT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
