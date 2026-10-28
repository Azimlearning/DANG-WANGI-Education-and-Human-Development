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
from api.i18n import kitwords
from api.i18n import overlay as overlay_module
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
    lang: str = "en",
) -> tuple[VerifiedEnvironment, dict]:
    """(the minted Environment, why it earned its label). Raises `LibraryBuildError` when the plan checks refuse the Plan and `VerificationFailed` when the
    verifier does. `lang` "ms" builds a Bahasa Melayu Environment from a Plan that an overlay has already translated (D-62); its slug is `<plan id>_ms`."""
    issues = check(plan, manifest, lang=lang)
    if issues:
        raise LibraryBuildError(f"{plan.id}: the plan checks refused it: {[i.code for i in issues]}")
    page = assemble(plan, manifest, lang=lang)
    citations, label, why = grounding(book, evidence, plan)
    env = verify_environment(
        slug=plan.id if lang == "en" else f"{plan.id}_{lang}",
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
    translations_dir: Path | None = None,
) -> list[tuple[Plan, VerifiedEnvironment]]:
    """Build every Plan in `plans_dir` (or just those whose id is in `only`), store the Environments and index each under its Plan's topic. With `translations_dir`, also
    build and link the Bahasa Melayu Environment of each Plan that has an overlay there."""
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
        if translations_dir is not None:
            translate(
                store,
                plan,
                env,
                manifest,
                version=version,
                book=book,
                evidence=evidence,
                public_origin=public_origin,
                kit_dist=kit_dist,
                interaction_seconds=interaction_seconds,
                directory=translations_dir,
            )
    return built


def translate(
    store: SqliteEnvironmentStore,
    plan: Plan,
    english: VerifiedEnvironment,
    manifest: kitmanifest.Manifest,
    *,
    version: str,
    book: CitationBook | None,
    evidence: Evidence | None,
    public_origin: str,
    kit_dist: Path,
    interaction_seconds: float,
    directory: Path | None = None,
) -> VerifiedEnvironment | None:
    """Build and store the Bahasa Melayu Environment of `plan` from its overlay, and link it to the English one with the overlay's review status. None when the
    Plan has no overlay. The Malay Environment is never indexed under a topic: a question is answered in English, and the switch asks for the translation (D-62)."""
    overlay = overlay_module.load_for(plan.id, directory)
    if overlay is None:
        return None
    try:
        malay = overlay_module.apply(plan, overlay)
    except overlay_module.OverlayError as exc:
        raise LibraryBuildError(str(exc)) from exc
    env, _ = build_environment(
        malay,
        manifest,
        version=version,
        book=book,
        evidence=evidence,
        public_origin=public_origin,
        kit_dist=kit_dist,
        interaction_seconds=interaction_seconds,
        lang="ms",
    )
    store.put_verified(env)
    # The Malay page carries the Kit's own Malay words too, so its Plan being reviewed is not enough (D-62).
    status = overlay.status if overlay.status == "draft" or kitwords.reviewed() else "draft"
    store.link_translation(
        english.env_id,
        env.env_id,
        lang="ms",
        status=status,
        reviewer=overlay.reviewer if status == "reviewed" else None,
        reviewed_on=overlay.reviewed_on if status == "reviewed" else None,
    )
    return env


_STOP = frozenset(
    "about above after again also another because before being between could does doing during each from have here into just like make many more most much "
    "need only other over really should show some such than that their them then there these they this those through under until very want were what when where "
    "which while will with would your work works using used explain understand teach help find".split()
)
_GENERIC = frozenset("speed light force heat energy water power waves mass cells pressure depth scale".split()) | frozenset(w[:5] for w in "speed light force heat energy water power waves mass cells pressure depth scale".split())
_POSSESSIVE = re.compile(r"([a-z]{3,})['\u2019]s\b")


def _stems(text: str) -> set[str]:
    """Word stems of five letters (a longer word keeps its first five), without everyday words and without the words under five letters."""
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 5 and w not in _STOP}


def match_by_name(question: str, entries: list[dict]) -> dict | None:
    """The Environment a question names, or None (D-59). Used only when the topic head is unsure, so the library can still answer "revise Hooke's law" or "Newton's
    cannonball" without a model call. A question names an Environment when it shares at least two word stems with the Environment's title, goal and id, a person's
    name in the title (Hooke's, Newton's) counting double; and only when no other Environment scores as high, so "Newton's law" is left for the full pipeline."""
    q = _stems(question)
    if not q or not entries:
        return None
    ids = [_stems(e["plan_id"].replace("_", " ")) - _GENERIC for e in entries]
    scored: list[tuple[int, dict]] = []
    for i, e in enumerate(entries):
        text = f"{e['title']} {e['goal']} {e['plan_id'].replace('_', ' ')}"
        # Strong words: a person's name in the title, and a word of the Environment's own id that no other id uses ("yeast", "titration").
        strong = {m[:5] for m in _POSSESSIVE.findall(e["title"].lower())} | {w for w in ids[i] if not any(w in other for j, other in enumerate(ids) if j != i)}
        shared = q & _stems(text)
        scored.append((len(shared) + len(shared & strong), e))
    scored.sort(key=lambda p: -p[0])
    best = scored[0][0]
    if best < 2 or (len(scored) > 1 and scored[1][0] >= best):
        return None
    return scored[0][1]


def best_entry(question: str, entries: list[dict]) -> dict:
    """Of the Environments indexed for one topic, the one whose title, goal and id share the most words with the question; the first (a stable order) on a
    tie. `entries` must not be empty."""
    words = set(re.findall(r"[a-z]+", question.lower()))

    def overlap(entry: dict) -> int:
        text = f"{entry['title']} {entry['goal']} {entry['plan_id']}".lower()
        return len({w for w in re.findall(r"[a-z]+", text) if len(w) > 3} & words)

    return max(entries, key=lambda e: (overlap(e), -entries.index(e)))
