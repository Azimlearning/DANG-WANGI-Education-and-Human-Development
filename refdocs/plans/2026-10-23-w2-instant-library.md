# Plan: W2, instant and free library hits

> Workstream W2 of `refdocs/plans/2026-10-22-completion-roadmap.md`. Decision: D-42. Execution doc: `refdocs/execution/2026-10-23-w2-instant-library.md`. Meets the first half of P5's exit criterion. **Written after the build** (the repo has done this before; the deviation is in the changelog).

## Why this exists

The PRD's P5 exit criterion is "a covered topic opens in under one second with no model call". The code did not do that: the library lookup ran after the routing fallback (a possible paid call) and the written explanation (always a paid call), and it matched only the exact canonical question. There was no live Instantiate path, and nothing put the 16 hand-written, corpus-checked Environments into the store the API serves from.

## What's already covered

The store and the delivery gate (every hit is re-checked), the question cache, the 16 hand-written Plans (`data/plans`) with their `kit-verified` citations, and the local router with its calibrated per-head gates.

## Scope

**In:**
- The library is consulted first, before routing or any paid step: (a) the exact question asked before, with the written answer kept beside it; (b) a topic the LOCAL router recognises with at least 0.55 confidence, served from a new topic index with the hand-written Plan's own `note` as the words.
- A topic index in the store (`library_topics`) and a shared builder (`api/pipeline/library.py`) that `eval/environments/build.py` and a new seeding command (`python -m api.library_seed`) both use.
- A stored Environment that a planner reproduces byte for byte is delivered as the stored one, not a crash.

**Out, with reasons:**
- Flag-evicts-and-writes-a-regression-eval (the other half of the P5 criterion): it needs decisions about who may flag and when a flag takes a page down (D-11, D-27). Tracked as an open gap.
- Serving a library Environment for topics the router recognises only weakly: that is measured, not assumed (see Risks).
- Chapter shelves and the Shelf presentation: W6.

## Approach

`run.py` calls `_from_library` right after intake. It asks the store for the exact question; failing that it asks the router WITHOUT the model fallback, and serves `best_entry` of the topic's indexed Environments. Both paths go through `deliver`, so a withdrawn, stale or tampered row is refused and the request falls through to the normal pipeline. Generated Environments store the explanation that streamed with them, so a repeat needs no call for the words either.

## Risks and unknowns

| Risk | Confidence | Mitigation |
|---|---|---|
| The router serves the wrong topic's Environment | The 0.55 threshold comes from a 42-question spot check judged by the build assistant, not a teacher (`refdocs/evidence/2026-10-18-p1b-router-spot-check.md`). On the 24 golden vertical questions the local router recognised 15 at 0.55 or more, all of them the right topic; the golden set is the project's own and may overlap the router's training data (unchecked) | `ASSUMED` in D-42; re-measure with a teacher's blind labels (W11); the gate and the Environment's own checks still apply, so a wrong topic costs a mismatched page, not an unverified one |
| The seeded library is stale after a Kit change | Known | The gate refuses a stale row; re-run `python -m api.library_seed` |
| A topic has no seeded Environment | Certain for 37 of 53 topics | It falls through to the normal pipeline |

## Definition of done

- With a seeded library, a question about a covered topic, asked of a spy provider, makes zero provider calls, returns the hand-written Plan's words and the stored Environment, and does so in under a second once the router is loaded.
- A repeated question makes zero provider calls and returns the same words and Environment.
- A topic below the threshold, with nothing seeded, a withdrawn row, or no router all fall through to the normal pipeline.
- `eval/environments/build.py` and the seeding command build through one function; all 16 Environments still verify as `kit-verified`.
