# Synapse v4: Build Status

> **Read this first to know where we are.** Updated at the end of every build session. Phases and scope come from `refdocs/synapse-v4-PRD.md` section 6. Don't reorder phases without updating this file and saying why (CLAUDE.md "keep docs current").

**Build philosophy:** walking skeleton first. One Environment, end to end, through the full trust path (generate, scan, render, mint, gate, sandbox) on fakes, before building the second of anything. Evidence is measured, never asserted. The Kit grows from measured gaps.

**Right now:** Nothing is built. This project was scaffolded on 2026-10-16: the docs, agent config, and the P0 plan exist; no code does. The next session starts at `refdocs/plans/2026-10-16-p0-walking-skeleton-census.md`.

---

## Phase checklist

| Phase | Scope | Status |
|---|---|---|
| P0 | Walking skeleton and coverage census | ⬜ Plan and execution docs written; no code |
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
| Workspace and toolchain | uv project plus pnpm workspace (`web`, `packages/schema`, `packages/kit`); Python 3.13 | ⬜ |
| Wire schema and codegen | TypeScript source, codegen to strict Pydantic, drift check; ported from Arcana v2 with provenance | ⬜ |
| Settings, fake LLM, spend ledger and cap | Fakes default; live mode refuses to start without a cap and key | ⬜ |
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

---

## Known gaps

- **No code exists.** Everything under "Done" in the PRD roadmap is a plan.
- **The first vertical is undecided** (D-09). The P0 census decides it.
- **The oracle is the hardest open problem** (PRD A-5): what independent reference says a science micro-model is true. The textbook worked-example bet is unmeasured.
- **The verifier's accuracy has never been measured** in any prior build. L6 produces the first number (P1).
- **Kit size and API are guesses** (A-2). The census and P1 spikes replace them.
- **Cost of a Compose-lane environment is unmeasured** (A-4). The v3 figure of about $0.19 is for whole-document generation.
- **Isolation for a public deploy is undecided** (A-10). `node:vm` is not isolation.
- **Corpus legality is unconfirmed** (A-8). Four Chemistry experiment books are image-only PDFs with no text layer and need OCR, which is not installed.
- **Deploy gate, rate limits and auth do not exist** and are deliberately deferred (D-11). The API must not be exposed.
- **No file-structure doc is written.** A file map of a project with no files would be fabrication; it becomes worth writing once there is a tree to describe.
- **No parity doc.** The four packages are one product joined by generated artefacts, not feature-parity surfaces.
- **No test suite yet.** Tracked here; the first tests arrive with P0 task 2.
- **Naming** ("Synapse" collision, A-14) is open.
