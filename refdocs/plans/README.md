# Plans

> **MANDATORY:** Before implementing any non-trivial feature, a plan document must exist in this folder.
> A plan covers **what** and **why**: goal, scope, constraints, risks, definition of done.
> The **how** and **in what order** belongs in `refdocs/execution/`. When the two merge, both stop being read.

## Naming convention

`YYYY-MM-DD-<slug>.md`: the date the plan was written, then a short kebab-case slug.

**The execution doc uses the identical filename** in `refdocs/execution/`. Same date, same slug: that mirroring is how you find a plan's other half without opening anything. If a plan gets superseded, write a new one and mark the old row Superseded; don't rewrite history in place.

## Required sections in every plan

1. **Why this exists:** the problem, in the user's terms
2. **What's already covered:** what needs no work, so nobody rebuilds it
3. **Scope:** what's in, and what's explicitly out *with reasons*
4. **Approach:** the shape of the solution
5. **Risks & unknowns:** with honest confidence levels. "I read this library's docs" and "I think this library does that" are different rows.
6. **Definition of done:** phrased as observable facts, not intentions

## Index

Add a row when you write a plan. Update the status when it moves: a stale index is how a project ends up with three plans for the same thing.

Status vocabulary: `Draft` · `In progress` · `Done` · `Blocked` · `Superseded` · `On hold`

| File | Description | Status |
|---|---|---|
| [2026-10-16-p0-walking-skeleton-census.md](2026-10-16-p0-walking-skeleton-census.md) | P0: walking skeleton and coverage census | Done (the owner delegated the vertical choice; the census stays an estimate) |
| [2026-10-16-v4-enhancement-audit.md](2026-10-16-v4-enhancement-audit.md) | Audit of every wanted v4 enhancement against the PRD | Done |
| [2026-10-16-p1-kit-core-and-verification.md](2026-10-16-p1-kit-core-and-verification.md) | P1: Kit core, provenance, L1 to L3, L6 baseline, isolation spike | In progress |
| [2026-10-16-p1b-models-track.md](2026-10-16-p1b-models-track.md) | P1b: trained local models (multi-head router) and the misconception matcher | Draft |
