# Synapse v4: Build Status

> **Read this first to know where we are.** Updated at the end of every build session. Phases and scope come from `refdocs/synapse-v4-PRD.md` section 6. Don't reorder phases without updating this file and saying why (CLAUDE.md "keep docs current").

**Build philosophy:** walking skeleton first. One Environment, end to end, through the full trust path (generate, scan, render, mint, gate, sandbox) on fakes, before building the second of anything. Evidence is measured, never asserted. The Kit grows from measured gaps.

**Right now:** everything that can be built on fakes in the cloud is built: P0, P1, P1b done; P2, P3, P4, P5 and P6 done for their cloud scope. The Mark 3 pipeline (D-23) runs end to end on fakes with real Chromium verification and produces **11 verified Environments, 3 Physics, 3 Biology and 5 Chemistry** (D-19 asked for 3 per subject), each with a hand-written Plan. No paid call has ever been made and no live provider class exists. **What waits for the owner:** the first paid run (confirm an amount; proposed canary up to $0.09, then 9 questions, projected $0.09 to $0.52, hard bound $0.80, suggested `LLM_MONTHLY_CAP_USD` $1.00; see `refdocs/evidence/2026-10-16-p3-cost-projection.md`), loading the textbook corpus locally (A-8), matching the catalogue to the owner's experiment documents, and a fresh adversarial review. The kit-guardian P3 review is answered except the items listed under Known gaps.

---

## Phase checklist

| Phase | Scope | Status |
|---|---|---|
| P0 | Walking skeleton and coverage census | ✅ Tasks 1 to 9 done and verified. The owner delegated the vertical choice (D-18); the census is an estimate not reviewed row by row |
| P1b | Models track (trained local models) | ✅ Cloud scope done: audited dataset, baselines, trained and exported router, parity, gates, model card, router with LLM fallback, misconception matcher. Retrain on the full KSSM data and an embedding comparison are deferred to local |
| P1 | Kit core and verification harness | ✅ Cloud scope done and verified (provenance, L1 to L3, L6 baseline, hostile set, isolation spike, reset/table/graph, two review rounds of which the second did not complete). Open: a fresh adversarial review, and the host-side DOM check noted in D-24 |
| P2 | Evidence: corpus, retrieval, citations | ✅ Cloud scope done: corpus format, BM25, exact quotation proof, `kit-verified` rule at mint and gate, experiment catalogue (metadata). Proved against a synthetic corpus only; the real corpus is loaded locally (A-8) |
| P3 | Mark 3 pipeline and the first vertical | 🔶 Done on fakes: router, planner, plan checks (PLAN-001 to 016), skeleton assembler, typed slot fills, verify with a drop-fills retry, mint, gate, deliver, loading skeleton, prompt packs, fail-check registry, golden set, hostile set, cost projection. **Not done:** the first paid run (owner), a live provider class, the Free lane, the L4 wording check. Review findings S4, S7, S8, S10 and notes remain |
| P4 | Kit expansion by kit | ✅ Cloud scope done: 11 science models (3 Physics, 3 Biology, 5 Chemistry), 87 planted bugs for the new ones, 11 Environments verified. Wording and scope are unchecked against the textbook |
| P5 | Library and lifecycle | ✅ Cloud scope done: question cache through the gate, withdraw, restore, flag, stale by Kit hash, endpoints. Single operator (D-11) |
| P6 | Pedagogy | 🔶 Hint ladder, concept check, predict card and worked solution built, planned and verified on six Environments. Not built: spaced practice, difficulty adaptation, misconception follow-up in the UI |
| P7 | Reach and the deploy gate | ⬜ Not started |
| P8 | Evidence and learner study | ⬜ Not started |

Status vocabulary: use these exactly, and never round up:
- ⬜ **Not started**
- 🔶 **In progress**: say precisely what works and what doesn't
- ✅ **Done**: built *and* verified. If it compiles but was never run, it is not done.
- ⛔ **Blocked**: name the blocker and who/what unblocks it

---

## P0: Walking skeleton and coverage census (done)

| Item | Approach | Status |
|---|---|---|
| Workspace and toolchain | uv project plus pnpm workspace (`web`, `packages/schema`, `packages/kit`); Python 3.13 | ✅ Verified in the cloud container |
| Wire schema and codegen | TypeScript source, codegen to strict Pydantic, drift check; ported from Arcana v2 with provenance | ✅ Drift check proven to fail and recover; 6 strictness tests |
| Settings, fake LLM, spend ledger and cap | Fakes default; live mode refuses to start without a cap and key | ✅ 10 tests. No live provider by design until P3 (D-15). Pricing and model ids still ASSUMED |
| Kit v0 | `environment`, `slider`, `readout`, observable, bridge, Hooke's law; esbuild bundle; manifest; version lock | ✅ 31 tests; bundle 7752 bytes; lock refuses an unversioned change. The Hooke's law reference values are the author's own arithmetic, citation UNVERIFIED |
| Reference Environment | One hand-written Environment over Kit v0 (a walking-skeleton illustration, not the first vertical) | ✅ Minted and delivered; nine planted-defect variants |
| Verification v0 | L0 scan, post-process rules, Playwright render harness, mint, store, gate | ✅ as a P0 skeleton; superseded by the P1 verifier (L1 to L3 now catch `bad-bypass`). The gate still trusts the store (A-19) |
| API `/ask` on fakes | SSE: meta, text, environment block, done | ✅ 18 tests and a live `curl -N` |
| Web shell | Stream, hash check, `sandbox="allow-scripts"` iframe, Peek and Stage | ✅ 22 unit tests and 17 of 17 checks in real Chromium |
| Coverage census | 53 topics annotated with pattern, model kind, needed micro-component kinds, expected lane | ✅ Built, validated (18 tests), report generated. An estimate by one annotator. The owner delegated the decision it informed (D-18) instead of reviewing it |

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
| 2026-10-16 | P1 and P1b whole-repo state | `uv run pytest -q`; `pnpm -r test`; `ruff check api eval`; `pyright api eval`; `pnpm -r typecheck`; `pnpm codegen:check`; `eval/smoke/web_smoke.py` | 284 passed 1 skipped; Kit 100 and web 23 passed; lint, types, codegen clean; smoke 17 of 17 |
| 2026-10-16 | L6 planted-defect baseline | `uv run python eval/l6/run.py` | 56 of 61 refused; 0 of 12 neutral controls refused; 5 known misses listed in `refdocs/evidence/2026-10-16-p1-l6-baseline.md`. A regression baseline, not an unbiased rate |
| 2026-10-16 | Hostile set | `uv run python eval/hostile/run.py` | 20 of 20 blocked by two layers (the question case by API validation) |
| 2026-10-16 | Isolation spike | `uv run python eval/isolation/spike.py` | `unshare --net` works at no cost; `RLIMIT_AS` breaks Chromium; see the evidence note |
| 2026-10-16 | Router model | `uv run python eval/models/train_router.py`, `calibrate.py`; `pytest eval/models api/routing` | Beats majority and keyword baselines on every head (complexity narrowly); pure-Python equals scikit-learn on 538 of 538; artifact hash stable across two runs; card generated and tested for staleness |

| 2026-10-16 | Whole-repo state after P2 to P6 cloud work and the P3 review fixes | `uv run pytest -q` (463 passed, 1 skipped); `pnpm -r test` (Kit 228, web 23); `ruff check api eval`; `pyright api eval`; `pnpm -r typecheck`; `pnpm codegen:check`; `eval/smoke/web_smoke.py` | All clean; smoke 18 of 18 in Chromium. After the exemplar change: `pytest api/pipeline api/routes eval/cost` 134 passed |
| 2026-10-16 | L6 and hostile after the pedagogy components and relocks | `uv run python eval/l6/run.py`; `uv run python eval/hostile/run.py` | L6: 56 of 61 refused, 0 of 12 neutral controls refused, no surprise misses; hostile 20 of 20 blocked |
| 2026-10-16 | The breadth set | `uv run python eval/environments/build.py` | 11 Environments verified in Chromium and delivered through the gate: Physics 3, Biology 3, Chemistry 5 (`refdocs/evidence/2026-10-16-p4-environments.md`) |
| 2026-10-16 | Cost projection (no paid call) | `uv run python eval/cost/project.py` | Per Environment, mean over 24 golden questions; canary up to $0.09, then 9 questions projected $0.09 to $0.52, hard bound $0.80; suggested cap $1.00. ASSUMED prices and model ids |

---

## Known gaps

- **The first vertical is provisional** (D-18, Physics Form 5, chosen under the owner's delegation). The census it rests on is an estimate (one annotator, topic names only) and the owner can overturn the choice at any time.
- **The oracle is the hardest open problem** (PRD A-5): what independent reference says a science micro-model is true. The textbook worked-example bet is unmeasured. `hookes`' reference values are the author's own arithmetic.
- **The verifier is stronger but not proven.** P1 added provenance, independent references, a frozen realm and a runtime self-check (D-24), and the L6 baseline refuses 56 of 61 planted defects. The five it cannot see are on the record (a bug at one unsampled input, a wrong label, false prose without numbers, and two conditionals that only the student-time self-check catches). The planted set was grown while holes were found, so it is a regression baseline, not an unbiased rate. The first review round found 18 bypasses; the second round did not complete, so no one has attacked the fixed design.
- **The gate trusts the store** (A-19). No re-render on delivery and no signature on rows.
- **Kit size and API are guesses** (A-2). The census names 61 candidate science models for 53 topics but cannot say how many each topic really needs, so it neither supports nor refutes the size guess. It suggests the scene library may dominate effort (51 of 53 topics need scene parts).
- **Cost of a Compose-lane environment is unmeasured** (A-4). The v3 figure of about $0.19 is for whole-document generation. No paid call has ever been made in this repo.
- **Isolation for a public deploy is undecided** (A-10, partly confirmed). `unshare --net` verifies fine in this container; hosting, memory limits via cgroup and a browser-exploit answer remain for the deploy gate.
- **Corpus legality is unconfirmed** (A-8). Four Chemistry experiment books are image-only PDFs with no text layer and need OCR, which is not installed.
- **Deploy gate, rate limits and auth do not exist** and are deliberately deferred (D-11). The API must not be exposed.
- **Accessibility is checked only statically and in the harness** (names, `aria-valuetext`, 44 px targets, no overflow at 360 px). No screen reader, reduced-motion or keyboard-only pass has been done in a real browser.
- **No clean-checkout rebuild has been done.** `uv sync` and `pnpm install` were run incrementally, never from an empty clone.
- **No file-structure doc and no parity doc** are written; the tree now exists, so a file map is worth writing at the start of P1.
- **No model has ever written a Plan.** The planner, the fills and the explainer are exercised only by deterministic fakes. Whether a real model produces Plans that pass the checks, what it costs and how often it needs the retry are all unmeasured (A-4). The first paid run answers this.
- **The Free lane and the L4 wording check are not built.** A question the Kit cannot express gets the written answer; the `verifier_l4` pack is written but called by nothing.
- **Open kit-guardian P3 findings:** plan checks vs verifier parity beyond the dilution relation (S4); homogeneous-property silent continue and domain tests (S7); accessibility and 360 px tests per component beyond the render harness audit (S8); a soundness test for the fail-check registry's coverage (S10); string length caps on every plan field and fill-contract bypass probes. B1 and S1, S2, S3, S5 (dilution relation), S6, S9, S12 are fixed. The review itself is one round by one reviewer.
- **Every Environment is `model-checked` with an UNVERIFIED citation.** No textbook page has confirmed any formula, unit, wording or scope. The photosynthesis curve is a stylised teaching curve and says so.
- **Kit 0.1.0 is unreleased and relocked on each change** (D-29). Nothing public depends on it yet.
- **Naming** ("Synapse" collision, A-14) is open.

## Deferred to local (things the cloud container could not do)

- **Load the textbook corpus** (A-8): set `CORPUS_DIR`, ingest with `api/evidence/ingest.py`, then re-run the breadth set and add real citations to the Plans. Four Chemistry experiment books are image-only and need OCR.
- **Match the experiment catalogue** (`data/experiments/catalogue.json`) to the owner's experiment documents; every entry says `confirmed_by_person: false`.
- **The first paid run** (needs the owner's confirmed amount and a live provider class built against the provider SDK's current docs, rule 6).
- **Run all suites on the Windows machine** and confirm Kit sha and bytes are stable across platforms (line endings, esbuild version).
- **A fresh kit-guardian pass over D-24** (the second round was stopped by a safety classifier). Run it locally, ideally with a person watching.
- **Router retrain** on the full KSSM ingestion and an embedding comparison (D-20, A-9); download sizes were not testable here.
- **Model card check by a person:** the router measures agreement with an LLM teacher; sample 50 held-out questions and judge the labels yourself.

The work ran in a Linux container, not on the Windows dev machine. These were noted and left for a local Claude Code session:

- **`.env.example`**: the permission settings blocked reading and editing it. Add `DATA_DIR`, `LEDGER_PATH`, `LOG_LEVEL` and `KIT_DIST_DIR` (all optional; documented in `refdocs/guides/env_setup.md`).
- **Windows toolchain**: nothing here was run on the Windows machine (Node 24.11.0, pnpm 10.12.1, Python 3.13.14, uv 0.11.26; the container had Node 22.22.0, pnpm 10.28.0, Python 3.13.16, uv 0.11.32). Run `uv sync`, `pnpm install` and the suites there. A-12 stays ASSUMED.
- **Playwright Chromium**: it was preinstalled here (about 920 MB at `/opt/pw-browsers`), so no download happened. Locally run `uv run playwright install chromium` (Playwright is pinned to 1.56.0) and record the download size and free disk (17 GB free on C: at 94 percent when last checked).
- **`eval/smoke/web_smoke.py` is POSIX-only** (process groups via `start_new_session` and `killpg`). It needs a small adaptation, or WSL, on Windows.
- **Current uv and pnpm docs** (CLAUDE.md rule 6): docs.astral.sh and pnpm.io were unreachable, so config was written against `--help` output and Next's bundled docs. Re-read them.
- **Smoke screenshots** are written to `test-results/web-smoke/` (gitignored), so they exist only in the container. Rerun the smoke locally to get them.
- **The Task 5 manual check** (see the good fixture's slider move a readout) was replaced by the smoke; do a quick look locally.
