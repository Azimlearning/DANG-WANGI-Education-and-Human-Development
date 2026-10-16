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
| `api/pipeline/plan.py`, `plan_checks.py` | The Plan model (strict) and its checks, PLAN-001 to PLAN-017 |
| `api/pipeline/assemble.py`, `skeletons/*.html` | The deterministic assembler and the two skeletons (simulation, virtual experiment) |
| `api/pipeline/fill.py` | Contracts for the only place a model writes page code (custom slots) |
| `api/pipeline/failchecks.py` | The registry of every rule the verifier, plan checks, fills and gate can emit; tied to the code by a test |
| `api/pipeline/prompts.py`, `api/prompts/*.md` | Request builders and the versioned prompt packs (stable part above `=== VARIABLE ===`) |
| `api/pipeline/fakes.py` | The deterministic fake planner, filler and explainer used in fake mode |
| `api/routing/`, `api/models/` | The trained router (pure-Python inference), its gate, the keyword fallback, the misconception matcher |

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
| `data/plans/*.json` | The 17 hand-written golden Plans (one per Environment) |
| `data/experiments/catalogue.json` | Experiment metadata only; nothing matched to the owner's documents yet |
| `data/models/router/`, `api/models/artifacts/` | Router training data splits, metrics and the shipped model |
| `data/kssm_topics.json`, `data/misconceptions.json`, `data/hostile/`, `data/fixtures/` | Taxonomy, misconception list, hostile inputs, hand-written fixture pages |
| `eval/` | `census`, `cost`, `environments`, `golden`, `hostile`, `isolation`, `l6`, `models`, `plans` (the parity fuzzer), `smoke` (real-browser) |
| `refdocs/evidence/` | Generated reports (do not edit by hand): census, L6, hostile, environments, cost projection, model card |

## Docs

`refdocs/STATUS.md` (where we are), `synapse-v4-PRD.md` (what and why), `changelog/{CHANGELOG,DECISIONS}.md`, `plans/`, `execution/`, `guides/{env_setup,checklist,file_map}.md`. The order of authority is in `CLAUDE.md`.

## Not in git

`packages/kit/dist/`, `web/.next/`, `.venv/`, `node_modules/`, `data/ledger.db`, the local textbook corpus (`CORPUS_DIR`), any `.env`.
