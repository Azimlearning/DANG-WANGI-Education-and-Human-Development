# Execution Plans

> **MANDATORY:** Every plan in `refdocs/plans/` that moves to implementation must have a matching execution document here.
> An execution plan covers **how** and **in what order**: ordered tasks, file paths, commands, and a Verify step per task.
> Do not start coding a feature that has no execution doc. Write one first.

## Naming convention

`YYYY-MM-DD-<slug>.md`: **identical filename to its companion plan** in `refdocs/plans/`. Same date, same slug.

## Required sections in every execution plan

1. **Companion plan:** link to the plan doc, at the top
2. **Before starting:** preconditions, settings, what must already be green
3. **Tasks:** ordered and self-contained, each with:
   - the files it creates or modifies
   - the exact steps or commands
   - a **Verify** step: a real command and its expected result
4. **Wrap-up:** the STATUS / changelog / ADR checklist

**A task is done when its Verify passes**, not when the code compiles. That distinction is the entire value of this folder.

## Keeping these honest

If reality diverges from the doc mid-build, **edit the doc** and note it in the changelog's Deviations line. A plan that changed silently is a plan nobody trusts next time. Stale docs are worse than no docs.

## Index

| File | Companion plan | Status |
|---|---|---|
| [2026-10-16-p0-walking-skeleton-census.md](2026-10-16-p0-walking-skeleton-census.md) | [../plans/2026-10-16-p0-walking-skeleton-census.md](../plans/2026-10-16-p0-walking-skeleton-census.md) | Done |
| [2026-10-16-p1-kit-core-and-verification.md](2026-10-16-p1-kit-core-and-verification.md) | [../plans/2026-10-16-p1-kit-core-and-verification.md](../plans/2026-10-16-p1-kit-core-and-verification.md) | Done (cloud scope; see STATUS) |
| [2026-10-16-p1b-models-track.md](2026-10-16-p1b-models-track.md) | [../plans/2026-10-16-p1b-models-track.md](../plans/2026-10-16-p1b-models-track.md) | Done (cloud scope; see STATUS) |
| [2026-10-16-p3-mark3-pipeline.md](2026-10-16-p3-mark3-pipeline.md) | [../plans/2026-10-16-p3-mark3-pipeline.md](../plans/2026-10-16-p3-mark3-pipeline.md) | Done on fakes (cloud scope); the first paid run is waiting on the owner |
| [2026-10-16-p2-p5-p6-evidence-library-pedagogy.md](2026-10-16-p2-p5-p6-evidence-library-pedagogy.md) | [../plans/2026-10-16-p2-p5-p6-evidence-library-pedagogy.md](../plans/2026-10-16-p2-p5-p6-evidence-library-pedagogy.md) | Done (cloud scope) |
| [2026-10-16-p4-kit-expansion.md](2026-10-16-p4-kit-expansion.md) | [../plans/2026-10-16-p4-kit-expansion.md](../plans/2026-10-16-p4-kit-expansion.md) | Done (cloud scope) |
| [2026-10-18-p2-real-corpus-and-citations.md](2026-10-18-p2-real-corpus-and-citations.md) | [../plans/2026-10-18-p2-real-corpus-and-citations.md](../plans/2026-10-18-p2-real-corpus-and-citations.md) | In progress (tasks 4, 9, 10 not started) |
| [2026-10-22-completion-roadmap.md](2026-10-22-completion-roadmap.md) | [../plans/2026-10-22-completion-roadmap.md](../plans/2026-10-22-completion-roadmap.md) | In progress (W0 done) |
