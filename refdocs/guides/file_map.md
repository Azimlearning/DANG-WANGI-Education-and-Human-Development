# File map

> Where things are, as built on 2026-10-16. Each line says what the file is for and what it must not do. If you add a file that a new reader would not find by name, add a line here. Wire types live only in `packages/schema`; the Python copy in `api/schema/generated.py` is generated and never edited by hand.

## The trust path (read in this order)

| File | Role |
|---|---|
| `api/verify/scan.py` | L0: forbidden APIs, markup, absolute URLs, script sources |
| `api/postprocess.py` | Injects the CSP as the first element; refuses ambiguous markup |
| `api/verify/render.py` | The Chromium harness: loads the page at 360 px, presses real input, sweeps every control through its grid and extremes, audits accessibility |
| `api/verify/provenance.py` | L1: every number on the page traces to a control, a constant or a science model; units; forged actions |
| `api/verify/references.py` | L3: independent Python formulas for every science model, and the unit table |
| `api/verify/mint.py` | The only place a `VerifiedEnvironment` can be made; label rules (`guard_label`) |
| `api/verify/store.py` | SQLite store of what was minted; lifecycle, flags, the question cache; HMAC signing of rows |
| `api/verify/gate.py` | The delivery gate: re-hashes, re-scans, re-checks CSP, Kit bytes, label, withdrawn, signature |
| `packages/kit/src/lockdown.ts`, `watch.ts`, `audit.ts`, `provenance.ts` | The Kit's side: frozen intrinsics, runtime self-check, the audit the harness reads |

## The pipeline (Mark 3, D-23)

| File | Role |
|---|---|
| `api/pipeline/run.py` | The orchestrator: intake, route, explain, plan, assemble, verify, deliver; the degrade ladder; the trace |
| `api/pipeline/plan.py`, `plan_checks.py` | The Plan model (strict) and its checks, PLAN-001 to PLAN-020 |
| `api/pipeline/assemble.py`, `skeletons/*.html` | The deterministic assembler and the two skeletons (simulation, virtual experiment) |
| `api/pipeline/fill.py` | Contracts for the only place a model writes page code (custom slots) |
| `api/pipeline/failchecks.py` | The registry of every rule the verifier, plan checks, fills and gate can emit; tied to the code by a test |
| `api/pipeline/prompts.py`, `api/prompts/*.md` | Request builders and the versioned prompt packs (stable part above `=== VARIABLE ===`) |
| `api/pipeline/fakes.py` | The deterministic fake planner, filler, explainer, wording judge and Free page used in fake mode |
| `api/pipeline/wording.py`, `free.py`, `gaplog.py` | L4: the lines a judge reads and its strict verdict reader; the Free lane's page reader; the Kit gap log (W1, D-41) |
| `web/app/page.tsx`, `web/components/*`, `web/lib/turns.ts`, `recent.ts`, `theme.ts` | The V3-styled shell: top bar and Axi, study rail, conversation, lab bench column, honest badges, progress by real pipeline layers; the turn reducer, device-local recent pointers and the theme (W3, D-38) |
| `packages/kit/src/style.ts` | The Kit's one stylesheet, in its own module so the audit can compare it with the page's (D-43) |
| `api/pipeline/library.py`, `api/library_seed.py` | One builder for hand-written Plans, the topic index and `best_entry`; `python -m api.library_seed` fills the library (W2, D-42) |
| `eval/l4/`, `data/l4/` | The pinned L4 case set (25 planted wording defects, 16 true controls) and its scorer; a stub judge scores 0 |
| `api/routing/`, `api/models/` | The trained router (pure-Python inference), its gate, the keyword fallback, the misconception matcher |

| `api/pipeline/constants.py` | The table of well-known constants PLAN-020 checks (g, molar volume, speed of light, Avogadro) |
| `api/models/probes.py`, `data/probes.json` | The misconception probe: strict loader, threshold, the basis text (W5a, D-48) |
| `api/models/exam.py`, `data/exam_items.json` | The exam mirror items, strict loader and the reference marker (W5c, D-50) |
| `api/evidence/titles.py`, `web/lib/citation.ts` | A citation as a book title and a PDF page; the same rule on both surfaces (D-47) |
| `web/components/{ProbeCard,ExamCard,LabReport}.tsx`, `web/lib/{exam,labreport}.ts` | The probe card, the exam card (marked in the browser) and the lab report panel; Stage also holds Present mode (D-48 to D-51) |
| `api/export.py` | The one-file export and `chapter_pack`, several Environments in one offline file (D-32, D-51) |
| `eval/gallery/build.py` | Builds every Environment as an offline file, one chapter pack per subject and form, and a static index; output `gallery-output/` is ignored by git |
| `.github/workflows/ci.yml` | Kit and web tests, codegen drift, lint and types, the Python suite, hostile set, L6 and the Linux smoke |

## Services and API

| File | Role |
|---|---|
| `api/app.py` | FastAPI app: `/ask` (SSE), `/library`, `/library/{id}`, `/library/{id}/export`, flag, withdraw, restore, `/spend`, `/health` |
| `api/main.py` | `uvicorn api.main:app` entry |
| `api/core/settings.py`, `errors.py` | Settings (see `env_setup.md`) and the one error shape |
| `api/limits.py` | Per-client rate limit and the cap on questions in flight |
| `api/export.py` | The offline single-file export (D-32) |
| `api/llm/` | The LLM seam: `service.py` (cap, ledger, fallback), `ledger.py`, `pricing.py`, `models.py`, `providers/{fake,anthropic}.py` |
| `api/evidence/` | Corpus, citation proof, ingestion, experiment catalogue |
| `api/kit.py`, `api/kitmanifest.py` | Reading the built Kit and its manifest; `api/static.py` serves it |

## Kit (`packages/kit`)

| File | Role |
|---|---|
| `src/science/*.ts` | One file per science model: spec, reference cases, properties, grid; `science.test.ts` holds every planted bug; `spec.ts` is the registration framework |
| `src/{slider,readout,graph,table,reset,stepper,experiment,hints,concept_check,predict_card,worked_solution,text,constant,convert}.ts` | UI and pedagogy components |
| `src/manifest.ts` | The catalogue the planner and the checks read (`useWhen`, domain, topics) |
| `build.mjs`, `kit-lock.json` | esbuild bundle; refuses a changed released version (`--relock` for the unreleased 0.1.0, D-29) |

## Web (`web`) and schema (`packages/schema`)

| File | Role |
|---|---|
| `packages/schema/src/*.ts` | Wire types; `pnpm codegen` writes `api/schema/generated.py` |
| `web/app/page.tsx`, `web/app/e/[id]/page.tsx` | The chat shell and the shared-link page |
| `web/components/EnvironmentFrame.tsx` | The sandbox host: re-hashes, `sandbox="allow-scripts"` only, tears down on navigation or violation |
| `web/components/{Peek,Stage,Provenance,PeekSkeleton,ShareButton,ProgressPanel}.tsx` | Presentations and the provenance panel |
| `web/lib/{stream,sandbox,hash,library,progress}.ts` | Stream parsing, bridge messages, hashing, shared links, device-local progress |

## Data and evidence

| Path | What |
|---|---|
| `data/plans/*.json` | The 16 hand-written golden Plans (one per Environment); `data/plans/unsupported/` holds Plans no textbook states |
| `data/citations/pointers.json` | Citation id to document, PDF page, claim, topics, models and who checked it. Pointers only: no textbook text |
| `api/evidence/registry.py`, `api/pipeline/grounding.py` | Resolve a Plan's citation ids against the local corpus; decide `kit-verified` or `model-checked` |
| `data/experiments/catalogue.json` | Experiment metadata only; nothing matched to the owner's documents yet |
| `data/models/router/`, `api/models/artifacts/` | Router training data splits, metrics and the shipped model |
| `data/kssm_topics.json`, `data/misconceptions.json`, `data/hostile/`, `data/fixtures/` | Taxonomy, misconception list, hostile inputs, hand-written fixture pages |
| `eval/` | `census`, `cost`, `environments`, `golden`, `hostile`, `isolation`, `l6`, `models`, `plans` (the parity fuzzer), `smoke` (real-browser) |
| `refdocs/evidence/` | Generated reports (do not edit by hand): census, L6, hostile, environments, cost projection, model card |

## Docs

`refdocs/STATUS.md` (where we are), `synapse-v4-PRD.md` (what and why), `changelog/{CHANGELOG,DECISIONS}.md`, `plans/`, `execution/`, `guides/{env_setup,checklist,file_map}.md`. The order of authority is in `CLAUDE.md`.

## Test guard

`conftest.py` at the repo root makes every test refuse a connection or a name lookup to anything but loopback (D-34); `api/conftest.py` adds the stricter `no_network` fixture. `eval/models/` also holds the router spot check and the misconception probe set and its evaluation. `eval/evidence/leak_check.py` finds textbook text in any file git would add; run it before `git add` (rule 13).

## Not in git

`packages/kit/dist/`, `web/.next/`, `.venv/`, `node_modules/`, `data/ledger.db`, the local textbook corpus (`CORPUS_DIR`), any `.env`.
