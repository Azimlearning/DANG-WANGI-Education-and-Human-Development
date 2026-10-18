# Synapse v4: Build Status

> **Read this first to know where we are.** Updated at the end of every build session. Phases and scope come from `refdocs/synapse-v4-PRD.md` section 6. Don't reorder phases without updating this file and saying why (CLAUDE.md "keep docs current").

**Build philosophy:** walking skeleton first. One Environment, end to end, through the full trust path (generate, scan, render, mint, gate, sandbox) on fakes, before building the second of anything. Evidence is measured, never asserted. The Kit grows from measured gaps.

**Next:** the local session is under way (started 2026-10-18; its prompt is `refdocs/guides/local_handoff.md`). Steps 0, 1 and 2 (the law citations) are done; The first paid run (a one-question canary, 2026-10-18, $0.0283 of an approved $0.20) worked end to end; see `refdocs/evidence/2026-10-18-p3-canary.md`. It does NOT show planning ability, because the planner was shown the golden Plan as its exemplar; the next step is `run.py --live --no-exemplar` on several questions, on the owner's stated amount (it states the cost, then waits for the amount to be typed). The `.env` has the key and a $3.00 cap; its `CORPUS_DIR` is still a placeholder and must be `C:/Users/User/synapse-corpus/text` (the API now refuses to start with a clear message otherwise).

**Right now:** everything that can be built on fakes in the cloud is built: P0, P1, P1b done; P2, P3, P4, P5 and P6 done for their cloud scope. The Mark 3 pipeline (D-23) runs end to end on fakes with real Chromium verification and produces **16 verified Environments, 5 Physics, 4 Biology and 7 Chemistry** (D-19 asked for 3 per subject), each with a hand-written Plan. **With the owner's textbook corpus loaded (2026-10-18) all 16 are `kit-verified`**: every citation is a quotation the corpus finds word for word on the stated page, re-proved at the gate (D-36). A teacher has not reviewed any of them. A 17th (cardiac output) was moved out of the set because no KSSM textbook states it. No paid call has ever been made. The live provider is now wired into `SYNAPSE_LLM_MODE=live` (D-34) and proved only against a mock transport. **What waits for the owner:** the first paid run, to be done locally (confirm an amount; proposed canary up to $0.08, then 9 questions, projected $0.08 to $0.49, hard bound $0.73, suggested `LLM_MONTHLY_CAP_USD` $1.00; see `refdocs/evidence/2026-10-16-p3-cost-projection.md`), confirming the corpus may be QUOTED publicly (A-8; local use is assumed from the owner supplying the files), matching the catalogue to the owner's experiment documents, and a fresh adversarial review. The kit-guardian P3 review is answered except the items listed under Known gaps.

---

## Phase checklist

| Phase | Scope | Status |
|---|---|---|
| P0 | Walking skeleton and coverage census | ✅ Tasks 1 to 9 done and verified. The owner delegated the vertical choice (D-18); the census is an estimate not reviewed row by row |
| P1b | Models track (trained local models) | ✅ Cloud scope done: audited dataset, baselines, trained and exported router, parity, gates, model card, router with LLM fallback, misconception matcher. Retrain on the full KSSM data and an embedding comparison are deferred to local |
| P1 | Kit core and verification harness | ✅ Cloud scope done and verified (provenance, L1 to L3, L6 baseline, hostile set, isolation spike, reset/table/graph, two review rounds of which the second did not complete). Open: a fresh adversarial review, and the host-side DOM check noted in D-24 |
| P2 | Evidence: corpus, retrieval, citations | ✅ Cloud scope done: corpus format, BM25, exact quotation proof, `kit-verified` rule at mint and gate, experiment catalogue (metadata). Proved against a synthetic corpus only; the real corpus is loaded locally (A-8) |
| P3 | Mark 3 pipeline and the first vertical | 🔶 Done on fakes: router, planner, plan checks (PLAN-001 to 016), skeleton assembler, typed slot fills, verify with a drop-fills retry, mint, gate, deliver, loading skeleton, prompt packs, fail-check registry, golden set, hostile set, cost projection. **Not done:** the first paid run (owner), the Free lane, the L4 wording check. The live provider class is wired (D-34) and mock-tested. Review findings S4, S7, S8, S10 and notes remain |
| P4 | Kit expansion by kit | ✅ Cloud scope done: 17 science models (5 Physics, 5 Biology, 7 Chemistry), about 180 planted bugs for the new ones, 17 Environments verified. Wording and scope are unchecked against the textbook |
| P5 | Library and lifecycle | ✅ Cloud scope done: question cache through the gate, withdraw, restore, flag, stale by Kit hash, endpoints. Single operator (D-11) |
| P6 | Pedagogy | 🔶 Hint ladder, concept check, predict card and worked solution built, planned and verified; device-local progress with an export code (D-33). Not built: spaced practice, difficulty adaptation, misconception follow-up in the UI, Amali mode scaffold, the exam mirror |
| P7 | Reach and the deploy gate | 🔶 Built so far: store attestation (D-31), request limits and `/spend`, share links, the offline single-file export (D-32). Not built: Bahasa Melayu, chapter packs, the MCP-Apps-shaped bridge, per-session and per-day limits, the deploy gate itself |
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

| 2026-10-16 | Six more models and Environments | `pnpm -r test`; `uv run pytest -q`; `uv run python eval/environments/build.py`; `eval/l6/run.py`; `eval/hostile/run.py`; `eval/smoke/web_smoke.py --no-build` | Kit 315 passed; 504 passed 1 skipped; 17 Environments verified and delivered; L6 56 of 61 refused with no false positives; hostile 20 of 20; smoke 18 of 18 |

| 2026-10-16 | Whole repo after the P3 review closed | `uv run pytest -q`; `pnpm -r test`; `eval/plans/fuzz.py` seeds 1 to 9; `eval/l6`, `eval/hostile`, `eval/environments/build.py`, `eval/smoke/web_smoke.py` | 565 passed 1 skipped; Kit 323, web 23; fuzz 0 parity gaps after two fixes; L6 56 of 61, 0 of 12 false positives; hostile 20 of 20; 17 Environments; smoke 18 of 18 (one earlier run 17 of 18, not reproduced) |

| 2026-10-16 | Whole repo after limits, share links, export and progress | `uv run pytest -q`; `pnpm -r test`; `eval/l6`; `eval/hostile`; `eval/environments/build.py`; `eval/smoke/web_smoke.py` | 581 passed 1 skipped; Kit 324, web 40; L6 56 of 61 refused, 0 of 12 false positives; hostile 20 of 20; 17 Environments; smoke 21 of 21 |

| 2026-10-16 | Clean-checkout rebuild | Fresh `git clone` of the pushed branch into an empty folder; `uv sync`; `pnpm install --frozen-lockfile`; `pnpm --filter @synapse/kit build`; `pnpm codegen:check`; ruff, pyright, typecheck; `pnpm -r test`; `pnpm --filter web build`; `uv run pytest -q`; `eval/smoke/web_smoke.py --no-build`; `eval/environments/build.py` | All succeeded with no manual steps: the Kit rebuilt to the locked hash `4da5421caad0`; 581 passed 1 skipped; Kit 324, web 40; smoke 21 of 21; 17 Environments; the regenerated report left the clone's git status clean (deterministic) |

| 2026-10-18 | Windows reproduction (Node 24.11.0, pnpm 10.28.0, Python 3.13.14, uv 0.11.26) | `uv sync`; `pnpm install --frozen-lockfile`; `uv run playwright install chromium`; `pnpm --filter @synapse/kit build`; `pnpm codegen:check`; `ruff check .`; `pyright api eval`; `pnpm -r typecheck`; `pnpm -r test`; `pnpm --filter web build`; `uv run pytest -q`; `eval/environments/build.py` | Kit hash `4da5421caad0` equals the lock on Windows; Kit 324 and web 40 passed; 589 passed 1 skipped (about 8 min); 17 Environments verified and the report unchanged; lint and types clean. Chromium headless shell was a 91 MiB download (free disk 13,965 to 13,494 MB). Three Windows-only faults fixed first (Kit build file URL, `no_network` vs the loopback `socketpair`, POSIX-only smoke) |
| 2026-10-18 | Smoke on Windows, repeated | `uv run python eval/smoke/web_smoke.py --no-build`, 11 runs, output of each kept | 21 of 21 every time; the 17-of-18 seen once in the cloud did not reproduce. A free-port precheck was added and shown to fire. The Linux branch was not run (WSL has no distribution) |
| 2026-10-18 | Live provider wiring and the ledger fix (D-34), no paid call | `uv run pytest api/llm api/routes api/test_network_guard.py` and the full suite | A truncated, empty or refused reply is booked at its real tokens (test: 1,000 in and 16,000 out on Sonnet 5.5 books $0.162); live mode with a key and cap builds `AnthropicProvider` and opens no socket; a rejected key gives a clean `provider_unavailable` event; any non-loopback connection or lookup in any test raises |
| 2026-10-18 | Verifier checks, round 3 (no attack page ran; the agent was stopped by a classifier) | `eval/l6/run.py` (4 runs); `eval/hostile/run.py`; `eval/plans/fuzz.py` seeds 10 to 19; `eval/environments/build.py`; `pytest api/verify api/pipeline` | L6 56 of 61, 0 of 12 false positives, no surprise misses; hostile 20 of 20; fuzz 142 of 300 minted, 0 parity gaps; 17 Environments verified; two real verifier gaps fixed (D-35) |
| 2026-10-18 | Router spot check and matcher measurement | `eval/models/spot_check.py` (judged by the assistant); `eval/models/misconception_eval.py` | Router domain 47 of 50, gated topic 36 of 42 right, all wrong topics at confidence 0.21 to 0.50; matcher 20 of 20 on statements, fires on 17 of 30 quiet questions (see the two evidence notes of 2026-10-18) |

| 2026-10-18 | Real corpus, citations and `kit-verified` (Step 2, D-36) | `uv run --group local python -m api.evidence.ingest ...` (26 PDFs, 15 min); `eval/environments/build.py --corpus ...`; an end-to-end API run on fakes with the real corpus; `eval/evidence/leak_check.py`; `uv run pytest -q` | 16 of 16 Environments `kit-verified`, each citation re-proved at the gate; `/ask`, `/library/<id>` and the offline export carry it; 6 Plan corrections and 1 Plan moved out; 624 passed 1 skipped; Kit 324, web 40; no textbook text in any committable file |

| 2026-10-18 | Paid-run readiness (Step 3, no paid call) | `uv run pytest -q` (648 passed, 1 skipped); `ruff`, `pyright`, `codegen:check`; `eval/evidence/leak_check.py`; a cost-auditor review; dry runs of `run.py --live` answering "no" | The ask shows the models, cap, spend, projection and hard bound and sends nothing unless an amount is typed; the amount is a real ceiling; canary g01 projected $0.0216 to $0.0468, hard bound $0.0835; nine questions $0.18 to $0.38 (script) and a hard bound of $0.75; six audit findings fixed |

---

## Known gaps

- **The first vertical is provisional** (D-18, Physics Form 5, chosen under the owner's delegation). The census it rests on is an estimate (one annotator, topic names only) and the owner can overturn the choice at any time.
- **The oracle is the hardest open problem** (PRD A-5): what independent reference says a science micro-model is true. The textbook worked-example bet is unmeasured. `hookes`' reference values are the author's own arithmetic.
- **The adversarial pass over D-24 is still owed, with a person watching.** A safety classifier stopped the agent again (2026-10-18). Three leads from its code reading are unproven (list markers on non-list elements, `<head>` text, visible `script`/`style` text) and scopes for navigation, the gate and store, and the plan and fill path were not reviewed; see `refdocs/evidence/2026-10-18-p1-guardian-round3.md`.
- **The verifier is stronger but not proven.** P1 added provenance, independent references, a frozen realm and a runtime self-check (D-24), and the L6 baseline refuses 56 of 61 planted defects. The five it cannot see are on the record (a bug at one unsampled input, a wrong label, false prose without numbers, and two conditionals that only the student-time self-check catches). The planted set was grown while holes were found, so it is a regression baseline, not an unbiased rate. The first review round found 18 bypasses; the second round did not complete, so no one has attacked the fixed design.
- **The gate trusts the store unless `STORE_ATTESTATION_KEY` is set** (A-19, D-31). With a key, rows are HMAC-signed and an unsigned or altered row is refused; there is still no re-render on delivery. The key must be set and kept out of the data directory at the deploy gate.
- **Kit size and API are guesses** (A-2). The census names 61 candidate science models for 53 topics but cannot say how many each topic really needs, so it neither supports nor refutes the size guess. It suggests the scene library may dominate effort (51 of 53 topics need scene parts).
- **Cost of a Compose-lane environment is unmeasured** (A-4). The v3 figure of about $0.19 is for whole-document generation. No paid call has ever been made in this repo.
- **Isolation for a public deploy is undecided** (A-10, partly confirmed). `unshare --net` verifies fine in this container; hosting, memory limits via cgroup and a browser-exploit answer remain for the deploy gate.
- **Corpus legality is unconfirmed for public quotation** (A-8). The owner supplied the textbooks on 2026-10-18 and local use is assumed; the exported offline file and the provenance panel show a short quotation, so confirm before any public deploy. The corpus lives outside the repository (`C:\Users\User\synapse-corpus`); the repository ignores `*.zip` and `*.pdf`.
- **The deploy gate and auth do not exist** and are deliberately deferred (D-11). A per-client per-minute limit, a cap on questions in flight and `GET /spend` now exist (in-process, per worker); per-session and per-day limits, student accounts and the rest of `refdocs/guides/checklist.md` do not. The API must not be exposed.
- **Accessibility is checked only statically and in the harness** (names, `aria-valuetext`, 44 px targets, no overflow at 360 px). No screen reader, reduced-motion or keyboard-only pass has been done in a real browser.
- **Clean-checkout rebuild: done 2026-10-16** from a fresh clone of the pushed branch (see the ledger), and reproduced on Windows on 2026-10-18 (also in the ledger) after three Windows-only fixes.
- **The Linux branch of the smoke was not run after its Windows edit** (WSL here has no distribution). The POSIX calls are the ones it used before; run it once on Linux or in CI.
- **`.env.example` is behind** and the permission settings deny the tools access to it. Paste these names with blank or safe values: `DATA_DIR=./data`, `LEDGER_PATH=` (absolute path; required in live mode), `LOG_LEVEL=INFO`, `KIT_DIST_DIR=./packages/kit/dist`, `VERIFY_INTERACTION_SECONDS=10`, `CORPUS_DIR=`, `STORE_ATTESTATION_KEY=`, `RATE_LIMIT_PER_MINUTE=20`, `MAX_CONCURRENT_ASKS=3`.
- **The file map is written** (`refdocs/guides/file_map.md`). No separate parity doc.
- **The misconception matcher is a topic detector** (fires on 17 of 30 questions that state no misconception; evidence note of 2026-10-18). The router's domain and topic heads were spot checked against the science on 50 questions by the assistant only; a teacher's blind labels are still needed.
- **A model-written Plan will be `model-checked`, not `kit-verified`,** because the planner prompt does not list the citation ids and so names none. Deciding whether a model-written Plan may earn `kit-verified` through retrieved citations (a citation proves the topic is in the book, not that the model's wording is right) is the owner's call; the first paid run does not need it.
- **Never run the API in live mode**: no auth, and the cap is its only bound. The paid run uses the script, not the server.
- **No model has ever written a Plan.** The planner, the fills and the explainer are exercised only by deterministic fakes. Whether a real model produces Plans that pass the checks, what it costs and how often it needs the retry are all unmeasured (A-4). The first paid run answers this.
- **The Free lane and the L4 wording check are not built.** A question the Kit cannot express gets the written answer; the `verifier_l4` pack is written but called by nothing.
- **kit-guardian P3 findings:** all answered (B1, S1 to S12 and the notes). One reviewer, one round; a second pass should be run locally. One smoke run failed once and was not reproduced (see the CHANGELOG).
- **`kit-verified` is not a teacher's review.** All 16 Environments carry corpus-proved citations (2026-10-18), but a quotation proves the words are on the page, not that the Environment matches them; the assistant read each page against its Plan, made 6 corrections and moved 1 Plan out (all in the changelog), and a person has not. Citations are pointers in `data/citations/pointers.json` marked `checked_by: assistant`; the quotations exist only beside the local corpus, so the labels reproduce only on a machine that has it. The photosynthesis curve is a stylised teaching curve and says so.
- **Student-facing citation text is the raw document id and PDF page** (for example `textbook-physics-physics-f5-removed`, page 36), not a book title and printed page. A friendlier display needs a wire-type change.
- **The Kit manifest's per-model `citation` fields still say UNVERIFIED**, and the `biology.cardiac_output` science model has no textbook basis. Fixing either is a Kit change (relock under D-29), not yet done.
- **Five Chemistry experiment scans (159 pages) and a few stray pages have no text layer** and are not OCRed, so the experiment catalogue cannot be matched to them yet.
- **Kit 0.1.0 is unreleased and relocked on each change** (D-29). Nothing public depends on it yet.
- **Naming** ("Synapse" collision, A-14) is open.

## Deferred to local (things the cloud container could not do)

- **Load the textbook corpus** (A-8): set `CORPUS_DIR`, ingest with `api/evidence/ingest.py`, then re-run the breadth set and add real citations to the Plans. Four Chemistry experiment books are image-only and need OCR.
- **Match the experiment catalogue** (`data/experiments/catalogue.json`) to the owner's experiment documents; every entry says `confirmed_by_person: false`.
- **The first paid run** (needs the owner's confirmed amount). The live provider class is wired and checked against the current docs (2026-10-18, D-34); `eval/golden/run.py --live` is not yet built.
- ~~**Run all suites on the Windows machine** and confirm Kit sha and bytes are stable across platforms (line endings, esbuild version).~~ Done 2026-10-18: the Kit sha equals the lock on Windows (checkout is CRLF via `core.autocrlf=true`; the bundle and the prompt hashes do not depend on it).
- **A fresh kit-guardian pass over D-24** (the second round was stopped by a safety classifier). Run it locally, ideally with a person watching.
- **Router retrain** on the full KSSM ingestion and an embedding comparison (D-20, A-9); download sizes were not testable here.
- **Model card check by a person:** the router measures agreement with an LLM teacher; sample 50 held-out questions and judge the labels yourself.

The work ran in a Linux container, not on the Windows dev machine. These were noted and left for a local Claude Code session:

- **`.env.example`**: STILL OPEN. The permission settings deny the tools access to it; the lines to paste are under Known gaps.
- ~~**Windows toolchain**~~ Done 2026-10-18 on Node 24.11.0, pnpm 10.28.0 (the pinned `packageManager`), Python 3.13.14, uv 0.11.26. A-12 is confirmed for this machine.
- ~~**Playwright Chromium**~~ Done 2026-10-18: a 91 MiB headless shell download (about 470 MB on disk); 13.5 GB free on C: at 95 percent afterwards.
- ~~**`eval/smoke/web_smoke.py` is POSIX-only**~~ Adapted 2026-10-18 (new process group and `taskkill /T /F` on Windows); the Linux branch is unchanged but was not re-run.
- ~~**Current uv and pnpm docs**~~ Re-read 2026-10-18: uv config is current; pnpm `onlyBuiltDependencies` works on 10.28 and is removed in pnpm 11 (`allowBuilds`, from 10.26).
- ~~**Smoke screenshots**~~ Regenerated locally in `test-results/web-smoke/` by the 2026-10-18 runs.
- **The Task 5 manual check** (see the good fixture's slider move a readout) was replaced by the smoke; do a quick look locally.
