# Synapse v4: Build Status

> **Read this first to know where we are.** Updated at the end of every build session. Phases and scope come from `refdocs/synapse-v4-PRD.md` section 6. Don't reorder phases without updating this file and saying why (CLAUDE.md "keep docs current").

**Build philosophy:** walking skeleton first. One Environment, end to end, through the full trust path (generate, scan, render, mint, gate, sandbox) on fakes, before building the second of anything. Evidence is measured, never asserted. The Kit grows from measured gaps.

**Right now:** P0 tasks 1 to 8 are built and verified: workspace, schema and codegen, fake LLM seam and ledger, Kit v0, the reference Environment with nine planted defects, verification v0 (L0, render harness, mint, store, gate), `/ask` on fakes, and the web shell with a real-browser smoke. Task 9, the coverage census, is written and validated but is an ESTIMATE awaiting the owner's review (`refdocs/evidence/2026-10-16-p0-census.md`); D-09 stays open until the owner decides. A kit-guardian review of the Kit and verification code found two blocking defects, both fixed (changelog). P1 has not started.

---

## Phase checklist

| Phase | Scope | Status |
|---|---|---|
| P0 | Walking skeleton and coverage census | 🔶 Tasks 1 to 8 done and verified. Task 9 (census) written and validated, awaiting the owner's review, so P0 is not done |
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
| Workspace and toolchain | uv project plus pnpm workspace (`web`, `packages/schema`, `packages/kit`); Python 3.13 | ✅ Verified in the cloud container |
| Wire schema and codegen | TypeScript source, codegen to strict Pydantic, drift check; ported from Arcana v2 with provenance | ✅ Drift check proven to fail and recover; 6 strictness tests |
| Settings, fake LLM, spend ledger and cap | Fakes default; live mode refuses to start without a cap and key | ✅ 10 tests. No live provider by design until P3 (D-15). Pricing and model ids still ASSUMED |
| Kit v0 | `environment`, `slider`, `readout`, observable, bridge, Hooke's law; esbuild bundle; manifest; version lock | ✅ 31 tests; bundle 7752 bytes; lock refuses an unversioned change. The Hooke's law reference values are the author's own arithmetic, citation UNVERIFIED |
| Reference Environment | One hand-written Environment over Kit v0 (a walking-skeleton illustration, not the first vertical) | ✅ Minted and delivered; nine planted-defect variants |
| Verification v0 | L0 scan, post-process rules, Playwright render harness, mint, store, gate | 🔶 Works and is tested (78 tests), but `bad-bypass` (a hand-typed wrong number) is NOT caught (needs L1, P1), obfuscated conditional navigation can still pass (A-10), and the gate trusts the store (A-19) |
| API `/ask` on fakes | SSE: meta, text, environment block, done | ✅ 18 tests and a live `curl -N` |
| Web shell | Stream, hash check, `sandbox="allow-scripts"` iframe, Peek and Stage | ✅ 22 unit tests and 17 of 17 checks in real Chromium |
| Coverage census | 53 topics annotated with pattern, model kind, needed micro-component kinds, expected lane | 🔶 Built, validated (18 tests), report generated. An estimate by one annotator. Owner review pending |

---|---|---|
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
| 2026-10-16 | P0 task 4 Kit v0 | `pnpm --filter @synapse/kit test`; `... build`; change `readout.ts` without a bump and build; restore and build | 31 passed (13 are the Hooke's law registration suite: real model accepted, 10 of 10 planted physics bugs refused); bundle 7752 bytes sha256 `ca8f09fe41ba`; the unversioned change exited 1 and removed `core.js`; the restored source rebuilt the identical hash |
| 2026-10-16 | P0 tasks 5 and 6 verification and planted defects | `uv run pytest api/verify -q` (78 tests); each fixture through `verify_environment` | Good fixture minted and delivered with its stored hash. Refused: fetch at scan, literal navigation at scan, dead control at render naming `'load'`, undeclared control, self-moving readout, unnamed controls, CSP-in-comment (hidden eval thrown), obfuscated navigation (frame left its document). `bad-bypass` minted, pinned as a known gap. One-byte tamper, a rewritten-consistent row containing fetch, a forged `canonical` label, a changed origin, an unbuilt Kit, a changed Kit under the same semver: all refused by the gate. Mint cannot be constructed, subclassed, changed, copied or pickled outside the verifier; an AST scan of `api/` and `eval/` finds the issuer only in `mint.py` |
| 2026-10-16 | kit-guardian B1 mutation test | Put the old naive `<head` injection back and run `pytest -k B1`; restore | With the old behaviour 4 B1 tests failed; with the fix all 7 pass |
| 2026-10-16 | P0 task 7 `/ask` | `uv run pytest api/routes -q`; `uvicorn` and `curl -N -X POST localhost:8000/ask` | 18 passed; the stream was `meta`, 7 `text_delta`, `environment`, `done` |
| 2026-10-16 | P0 task 8 web shell | `pnpm --filter web test`; `uv run python eval/smoke/web_smoke.py` | 22 passed; 17 of 17 real-browser checks (sandbox exactly `allow-scripts`, slider 0.040 m to 0.200 m, fetch from the frame blocked with a CSP violation, 360 px no scroll and 44 px targets, wrong hash never rendered, navigating frame torn down). Screenshots in `test-results/web-smoke/` (not committed) |
| 2026-10-16 | P0 task 9 census | `uv run python eval/census/census.py --check`; `uv run pytest eval -q` | OK: 53 rows, unique slugs, every cell in its vocabulary, every count sums to 53; 18 passed. NOT yet reviewed by the owner |
| 2026-10-16 | Whole-repo state at the end of the session | `uv run pytest -q`; `pnpm -r test`; `ruff check api eval`; `pyright api`; `pnpm -r typecheck`; `pnpm codegen:check` | 130 + 31 + 22 = 183 tests passed; ruff clean; pyright 0 errors; typecheck clean in 3 packages; codegen OK |

---

## Known gaps

- **The first vertical is undecided** (D-09). The census is an estimate (one annotator, topic names only). It ranks Physics first, Chemistry second, Biology third, and splits on Physics Form 4 (more strong topics) against Form 5 (Hooke's law exists, least custom drawing). The owner decides.
- **The oracle is the hardest open problem** (PRD A-5): what independent reference says a science micro-model is true. The textbook worked-example bet is unmeasured. `hookes`' reference values are the author's own arithmetic.
- **The verifier is only partly effective.** It does not catch a hand-typed wrong number in a readout (`bad-bypass`, needs L1 in P1). The L0 scan is text matching and the harness exercises only the inputs it thinks of, so an obfuscated handler that fires on an unreached condition can pass; only isolation closes that (A-10). Its detection rate on planted physics bugs in generated Environments has never been measured (L6, P1).
- **The gate trusts the store** (A-19). No re-render on delivery and no signature on rows.
- **Kit size and API are guesses** (A-2). The census names 61 candidate science models for 53 topics but cannot say how many each topic really needs, so it neither supports nor refutes the size guess. It suggests the scene library may dominate effort (51 of 53 topics need scene parts).
- **Cost of a Compose-lane environment is unmeasured** (A-4). The v3 figure of about $0.19 is for whole-document generation. No paid call has ever been made in this repo.
- **Isolation for a public deploy is undecided** (A-10). `node:vm` is not isolation.
- **Corpus legality is unconfirmed** (A-8). Four Chemistry experiment books are image-only PDFs with no text layer and need OCR, which is not installed.
- **Deploy gate, rate limits and auth do not exist** and are deliberately deferred (D-11). The API must not be exposed.
- **Accessibility is checked only statically and in the harness** (names, `aria-valuetext`, 44 px targets, no overflow at 360 px). No screen reader, reduced-motion or keyboard-only pass has been done in a real browser.
- **No clean-checkout rebuild has been done.** `uv sync` and `pnpm install` were run incrementally, never from an empty clone.
- **No file-structure doc and no parity doc** are written; the tree now exists, so a file map is worth writing at the start of P1.
- **Naming** ("Synapse" collision, A-14) is open.

## Deferred to local (things the cloud container could not do)

The work ran in a Linux container, not on the Windows dev machine. These were noted and left for a local Claude Code session:

- **`.env.example`**: the permission settings blocked reading and editing it. Add `DATA_DIR`, `LEDGER_PATH`, `LOG_LEVEL` and `KIT_DIST_DIR` (all optional; documented in `refdocs/guides/env_setup.md`).
- **Windows toolchain**: nothing here was run on the Windows machine (Node 24.11.0, pnpm 10.12.1, Python 3.13.14, uv 0.11.26; the container had Node 22.22.0, pnpm 10.28.0, Python 3.13.16, uv 0.11.32). Run `uv sync`, `pnpm install` and the suites there. A-12 stays ASSUMED.
- **Playwright Chromium**: it was preinstalled here (about 920 MB at `/opt/pw-browsers`), so no download happened. Locally run `uv run playwright install chromium` (Playwright is pinned to 1.56.0) and record the download size and free disk (17 GB free on C: at 94 percent when last checked).
- **`eval/smoke/web_smoke.py` is POSIX-only** (process groups via `start_new_session` and `killpg`). It needs a small adaptation, or WSL, on Windows.
- **Current uv and pnpm docs** (CLAUDE.md rule 6): docs.astral.sh and pnpm.io were unreachable, so config was written against `--help` output and Next's bundled docs. Re-read them.
- **Smoke screenshots** are written to `test-results/web-smoke/` (gitignored), so they exist only in the container. Rerun the smoke locally to get them.
- **The Task 5 manual check** (see the good fixture's slider move a readout) was replaced by the smoke; do a quick look locally.
