# Synapse v4: Build Status

> **Read this first to know where we are.** Updated at the end of every build session. Phases and scope come from `refdocs/synapse-v4-PRD.md` section 6. Don't reorder phases without updating this file and saying why (CLAUDE.md "keep docs current").

**Build philosophy:** walking skeleton first. One Environment, end to end, through the full trust path (generate, scan, render, mint, gate, sandbox) on fakes, before building the second of anything. Evidence is measured, never asserted. The Kit grows from measured gaps.

**Right now:** P0 tasks 1 to 3 are done and verified (workspace, wire schema and codegen, settings, fake LLM seam and spend ledger). Nothing from task 4 on exists: no Kit, no fixtures, no verifier, no `/ask`, no web app, no census. The next session starts at P0 task 4 in `refdocs/execution/2026-10-16-p0-walking-skeleton-census.md`.

---

## Phase checklist

| Phase | Scope | Status |
|---|---|---|
| P0 | Walking skeleton and coverage census | 🔶 Tasks 1 to 3 of 9 done and verified; tasks 4 to 9 not started |
| P1 | Kit core and verification harness | ⬜ Not started |
| P2 | Evidence: corpus, retrieval, citations | ⬜ Not started |
| P3 | Mark 3 pipeline and the first vertical | ⬜ Not started |
| P4 | Kit expansion by kit | ⬜ Not started |
| P5 | Library and lifecycle | ⬜ Not started |
| P6 | Pedagogy | ⬜ Not started |
| P7 | Reach and the deploy gate | ⬜ Not started |
| P8 | Evidence and learner study | ⬜ Not started |

Status vocabulary: use these exactly, and never round up:
- ⬜ **Not started**
- 🔶 **In progress**: say precisely what works and what doesn't
- ✅ **Done**: built *and* verified. If it compiles but was never run, it is not done.
- ⛔ **Blocked**: name the blocker and who/what unblocks it

---

## P0: Walking skeleton and coverage census (current phase)

| Item | Approach | Status |
|---|---|---|
| Workspace and toolchain | uv project plus pnpm workspace (`web`, `packages/schema`, `packages/kit`); Python 3.13 | ✅ Verified in the cloud container; `web/` does not exist yet (task 8) |
| Wire schema and codegen | TypeScript source, codegen to strict Pydantic, drift check; ported from Arcana v2 with provenance | ✅ Drift check proven to fail and recover; 6 strictness tests pass |
| Settings, fake LLM, spend ledger and cap | Fakes default; live mode refuses to start without a cap and key | ✅ 10 tests pass. No live provider by design until P3 (D-15). Pricing and model ids still ASSUMED |
| Kit v0 | `environment`, `slider`, `readout`, observable, bridge; esbuild bundle; manifest | ⬜ |
| Reference Environment | One hand-written Environment composed over Kit v0 (a walking-skeleton illustration, not the first vertical) | ⬜ |
| Verification v0 | L0 scan (ported from v3), Playwright render harness, mint, store, gate | ⬜ |
| API `/ask` on fakes | SSE: meta, text, environment block, done | ⬜ |
| Web shell | Stream, hash check, `sandbox="allow-scripts"` iframe, Peek and Stage | ⬜ |
| Coverage census | 53 topics annotated with pattern, model kind, needed micro-component kinds, expected lane | ⬜ |

---

## Verification ledger

What has actually been run, not what has been written. A row here needs a real command and a real result.

| Date | What was verified | How | Result |
|---|---|---|---|
| 2026-10-16 | Toolchain present on the dev machine | `uv --version`, `node --version`, `pnpm --version`, `python --version`, `git --version`; `df -h` | uv 0.11.26, Node 24.11.0, pnpm 10.12.1, Python 3.13.14, git 2.47.0; 17 GB free on C: at 94 percent. Python Playwright is **not** installed |
| 2026-10-16 | P0 task 1 workspace (cloud container, not the Windows machine) | `uv sync`; `uv run python -c "import fastapi, pydantic; print('ok')"`; `pnpm install`; `pnpm -r build`; `df -h` | All exit 0, printed `ok`. uv 0.11.32, Node 22.22.0, pnpm 10.28.0, Python 3.13.16. 30 GB free before and after |
| 2026-10-16 | P0 task 2 schema and codegen | `pnpm codegen`; `pnpm codegen:check`; rename `planSummary` without regenerating then `pnpm codegen:check`; revert and rerun; `uv run pytest api/schema -q` | Check OK (exit 0); after the rename exit 1; after the revert exit 0; 6 passed |
| 2026-10-16 | P0 task 3 settings, fake LLM, ledger, cap | `uv run pytest api -q`; `uv run ruff check api`; `uv run pyright api` | 16 passed (6 schema, 10 llm); ruff clean; pyright 0 errors. Includes: no network in fake mode, live config errors name `ANTHROPIC_API_KEY` and `LLM_MONTHLY_CAP_USD`, over-cap request refused with the provider spy uncalled, ledger row written |

---

## Known gaps

- **Little code exists.** Only P0 tasks 1 to 3 (workspace, schema, LLM seam). The Kit, verifier, API routes, web app and census are still plans.
- **The first vertical is undecided** (D-09). The P0 census decides it.
- **The oracle is the hardest open problem** (PRD A-5): what independent reference says a science micro-model is true. The textbook worked-example bet is unmeasured.
- **The verifier's accuracy has never been measured** in any prior build. L6 produces the first number (P1).
- **Kit size and API are guesses** (A-2). The census and P1 spikes replace them.
- **Cost of a Compose-lane environment is unmeasured** (A-4). The v3 figure of about $0.19 is for whole-document generation.
- **Isolation for a public deploy is undecided** (A-10). `node:vm` is not isolation.
- **Corpus legality is unconfirmed** (A-8). Four Chemistry experiment books are image-only PDFs with no text layer and need OCR, which is not installed.
- **Rule 6 only partly met for tooling.** The uv and pnpm docs sites were unreachable from the cloud container; config was written against `--help` output. Re-read the current docs when they are reachable.
- **Two toolchains.** STATUS and A-12 were written for the Windows machine (Node 24.11.0, pnpm 10.12.1); the cloud container has Node 22.22.0 and pnpm 10.28.0. A-12 stays ASSUMED.
- **Deploy gate, rate limits and auth do not exist** and are deliberately deferred (D-11). The API must not be exposed.
- **No file-structure doc is written.** A file map of a project with no files would be fabrication; it becomes worth writing once there is a tree to describe.
- **No parity doc.** The four packages are one product joined by generated artefacts, not feature-parity surfaces.
- **Test coverage is thin.** 16 Python tests exist (schema, LLM seam). `pnpm -r test` has never run anything (no TypeScript tests yet). No clean-checkout rebuild has been done.
- **Naming** ("Synapse" collision, A-14) is open.
