"""The seeded library (P5, D-42): hand-written Plans built into verified Environments, stored, and indexed by KSSM topic, so a question about a covered topic is
answered with no model call and no planning.

One implementation builds an Environment from a Plan, used by the library seeding command (`python -m api.library_seed`) and by `eval/environments/build.py`,
so the evidence report and the served library cannot drift apart. Nothing here weakens a check: the Plan goes through the plan checks, the deterministic
assembler and the full verifier, the label comes from `grounding`, and the stored row is re-checked by the delivery gate every time it is served.
"""

from __future__ import annotations

import re
from pathlib import Path

from api import kitmanifest
from api.evidence.registry import CitationBook
from api.kit import latest_version
from api.pipeline import plan as plan_module
from api.pipeline.assemble import assemble
from api.pipeline.grounding import grounding
from api.pipeline.plan import Plan
from api.pipeline.plan_checks import check
from api.verify.mint import Evidence, VerifiedEnvironment, verify_environment
from api.verify.store import SqliteEnvironmentStore

PLANS = Path(__file__).resolve().parents[2] / "data" / "plans"

INSTANTIATE_MIN_CONFIDENCE = 0.55
"""How sure the LOCAL topic head must be before a stored Environment is served without a model call. ASSUMED (D-42): taken from the 2026-10-18 spot check
(`refdocs/evidence/2026-10-18-p1b-router-spot-check.md`), where no wrong topic call out of 42 would have passed at 0.55. That is 42 questions judged by the build
assistant, not a teacher; it is a starting point to be re-measured with a person's labels (W11), not a guarantee."""


class LibraryBuildError(ValueError):
    """A Plan could not be built into an Environment. The message names the Plan and why."""


def build_environment(
    plan: Plan,
    manifest: kitmanifest.Manifest,
    *,
    version: str,
    book: CitationBook | None,
    evidence: Evidence | None,
    public_origin: str,
    kit_dist: Path,
    interaction_seconds: float,
) -> tuple[VerifiedEnvironment, dict]:
    """(the minted Environment, why it earned its label). Raises `LibraryBuildError` when the plan checks refuse the Plan and `VerificationFailed` when the
    verifier does."""
    issues = check(plan, manifest)
    if issues:
        raise LibraryBuildError(f"{plan.id}: the plan checks refused it: {[i.code for i in issues]}")
    page = assemble(plan, manifest)
    citations, label, why = grounding(book, evidence, plan)
    env = verify_environment(
        slug=plan.id,
        title=plan.title,
        raw_html=page.html,
        lane="instantiate",
        label=label,  # type: ignore[arg-type]  # "kit-verified" or "model-checked", from `grounding`
        kit_version=version,
        citations=citations,
        plan_summary=plan.goal,
        public_origin=public_origin,
        kit_dist=kit_dist,
        interaction_seconds=interaction_seconds,
        plan_models=plan.model_summaries(),
        evidence=evidence,
    )
    return env, why


def seed(
    store: SqliteEnvironmentStore,
    *,
    kit_dist: Path,
    public_origin: str,
    book: CitationBook | None = None,
    evidence: Evidence | None = None,
    interaction_seconds: float = 10.0,
    plans_dir: Path = PLANS,
    only: set[str] | None = None,
) -> list[tuple[Plan, VerifiedEnvironment]]:
    """Build every Plan in `plans_dir` (or just those whose id is in `only`), store the Environments and index each under its Plan's topic."""
    version = latest_version(kit_dist)
    manifest = kitmanifest.load(kit_dist, version)
    built: list[tuple[Plan, VerifiedEnvironment]] = []
    for path in sorted(plans_dir.glob("*.json")):
        plan = plan_module.parse(path.read_text(encoding="utf-8"))
        if only is not None and plan.id not in only:
            continue
        env, _ = build_environment(
            plan,
            manifest,
            version=version,
            book=book,
            evidence=evidence,
            public_origin=public_origin,
            kit_dist=kit_dist,
            interaction_seconds=interaction_seconds,
        )
        store.put_verified(env)
        store.index_topic(plan.topic, env.env_id, plan_id=plan.id, title=plan.title, goal=plan.goal, note=plan.note)
        built.append((plan, env))
    return built


def best_entry(question: str, entries: list[dict]) -> dict:
    """Of the Environments indexed for one topic, the one whose title, goal and id share the most words with the question; the first (a stable order) on a
    tie. `entries` must not be empty."""
    words = set(re.findall(r"[a-z]+", question.lower()))

    def overlap(entry: dict) -> int:
        text = f"{entry['title']} {entry['goal']} {entry['plan_id']}".lower()
        return len({w for w in re.findall(r"[a-z]+", text) if len(w) > 3} & words)

    return max(entries, key=lambda e: (overlap(e), -entries.index(e)))
