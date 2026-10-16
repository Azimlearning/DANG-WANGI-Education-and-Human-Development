# Execution: P0 Walking skeleton and coverage census

> Plan: `refdocs/plans/2026-10-16-p0-walking-skeleton-census.md`. Tasks run top to bottom. Each task carries its own **Verify** step, and a task is not done until its Verify actually passes, not when the code compiles.
> If reality diverges from this doc, **edit this doc** (CLAUDE.md rule 4). A stale execution doc is worse than none.

## Before starting

- Read `CLAUDE.md`, `.claude/memory/preflight.md`, the PRD sections 3 and 6, and `refdocs/changelog/DECISIONS.md`.
- Toolchain observed 2026-10-16: Python 3.13.14, uv 0.11.26, Node 24.11.0, pnpm 10.12.1, git 2.47.0. Re-check with `uv --version`, `node --version`, `pnpm --version`.
- Disk: 17 GB free on C: (94 percent used). Record free space before and after task 6.
- No API key is needed. Leave `SYNAPSE_LLM_MODE=fake`. No paid call is made in P0.
- Source repositories to port from are `Azimlearning/Arcana-v2` (commit `21c6dcf5`) and the `Azimlearning/GenUI-Education` monorepo's `Synapse-V3/` folder. Have local clones available (their paths are machine-specific and deliberately not recorded here). They are read-only references. Never edit them from here.
- Open assumptions that P0 does not depend on but should not be forgotten: A-8 (corpus legality), A-10 (isolation), A-11 (exposure reading), A-14 (name).

---

## Task 1: Workspace and toolchain

**Files:** `pyproject.toml`, `uv.lock`, `package.json`, `pnpm-workspace.yaml`, `.python-version`, `api/__init__.py`, `packages/schema/package.json`, `packages/kit/package.json`, `eval/__init__.py`.

**Steps:**
1. Read the current uv project and pnpm workspace docs (rule 6). Do not copy config from memory or from Arcana v2.
2. Create a uv project requiring Python 3.13 with: fastapi, pydantic v2, uvicorn, httpx, sse-starlette (or the framework's own streaming; read the docs), pytest, ruff, pyright.
3. Create `pnpm-workspace.yaml` listing `web` and `packages/*`. Root scripts `codegen` and `codegen:check` (they may call a stub until task 2).
4. Create empty package manifests for `packages/schema` and `packages/kit`.

**Verify:**
- `uv sync` exits 0 and `uv run python -c "import fastapi, pydantic; print('ok')"` prints `ok`.
- `pnpm install` exits 0 and `pnpm -r build` exits 0.
- Record disk free before and after in STATUS.

## Task 2: Wire schema and codegen

**Files:** `packages/schema/src/{blocks,events,index}.ts`, `packages/schema/codegen/to_python.ts`, `api/schema/generated.py`, `api/schema/test_strict.py`.

**Steps:**
1. Read Arcana v2's `packages/schema` and its codegen in full. Note its conventions (an `/** @int */` marker on its own line; no `extends`; no generics; a union of blocks as `type` literals). Port with a provenance comment.
2. Define: `BlockMeta`, `ErrorEnvelope`, `EnvironmentBlock` (id, title, lane, label, kitVersion, htmlSha256, html, citations, planSummary), and the SSE events `meta`, `text_delta`, `environment`, `error`, `done`.
3. `lane` is `instantiate | compose | free`. `label` is `dev-fixture | kit-verified | model-checked | reviewed | canonical`; only `dev-fixture` is reachable in P0 and it is removed in P1.
4. Generate strict Pydantic models (`extra="forbid"`, `strict=True`). Add a drift check.

**Verify:**
- `pnpm codegen` then `pnpm codegen:check` exits 0.
- Rename a field in `blocks.ts` without regenerating: `pnpm codegen:check` exits 1. Revert: exits 0.
- `uv run pytest api/schema -q`: an unknown field is rejected; `"1"` is rejected for an integer field; an unknown `lane` is rejected.

## Task 3: Settings, fake LLM seam, spend ledger and cap

**Files:** `api/core/settings.py`, `api/llm/{types,service,fake,ledger,pricing}.py`, `api/llm/test_*.py`.

**Steps:**
1. Read Arcana v2's `api/llm/` in full. Port the minimum: request and result types, a deterministic fake provider (output derived from a hash of the prompt), a SQLite ledger at `data/ledger.db`, the cap check before send, and startup validation.
2. Settings: `SYNAPSE_LLM_MODE` (default `fake`), `LLM_MONTHLY_CAP_USD`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `PUBLIC_ORIGIN`. Live mode without a key or without a cap fails at startup and names the variable.
3. Pricing table with the figures in `synapse-v4-sources.md`, marked `ASSUMED` until checked against the provider's pricing page before the first live call.

**Verify:** `uv run pytest api/llm -q` includes and passes:
- default mode is fake and a socket-blocking fixture proves no network call is made;
- live mode without `ANTHROPIC_API_KEY` raises at startup naming `ANTHROPIC_API_KEY`; without a cap, naming `LLM_MONTHLY_CAP_USD`;
- a request whose projected cost exceeds the cap is refused and the provider spy was not called;
- a ledger row is written with purpose, tokens and cost.

## Task 4: Kit v0

**Files:** `packages/kit/src/{observable,environment,slider,readout,bridge,science_hookes,index}.ts`, `packages/kit/build.mjs`, `packages/kit/src/manifest.ts`, `packages/kit/src/*.test.ts`.

**Steps:**
1. Read the current esbuild and Vitest docs (rule 6).
2. `observable`: get, set, subscribe, map. `environment({title, note})`: mounts a title, a study-note card, a stage region, controls and readouts, using a small set of CSS variables. `slider({id,label,unit,min,max,value})`: returns an observable and clamps. `readout({label,unit,value})`: **throws** unless `value` is an observable. `bridge`: posts `synapse_ready` after first paint, `synapse_event` on a control change, `synapse_error` on a caught error (names kept from v3).
3. `science_hookes`: one tiny closed-form micro-model, `extension = load / k`, whose manifest entry carries a citation field set to `UNVERIFIED (corpus not loaded until P2)`.
4. Build an IIFE bundle to `packages/kit/dist/0.0.1/core.js` and generate `dist/0.0.1/manifest.json` (ids, signatures, preconditions, one-line docs, citation).

**Verify:**
- `pnpm --filter kit test` passes: observable propagation; slider clamps; `readout` rejects a plain number; bridge posts the right message types; the manifest lists every exported micro-component id.
- `pnpm --filter kit build` writes `core.js` and `manifest.json`; record the bundle size.

## Task 5: Reference Environment fixture

**Files:** `data/fixtures/envs/reference-spring.html`, `data/fixtures/envs/reference-spring.plan.json`, plus three planted-defect variants alongside it: `reference-spring.bad-fetch.html`, `reference-spring.bad-dead-control.html`, `reference-spring.bad-bypass.html`.

**Steps:**
1. Write the good fixture by hand: it loads `/vendor/kit/0.0.1/core.js` and composes a slider (load), the Hookes micro-model, and a readout of the extension. It is an illustration of the lane, **not the first vertical** (D-09).
2. Write the three broken variants: one calls `fetch`, one has a slider that is not wired to any readout, one writes a readout number by hand instead of from an observable (to be caught by L1 in P1; in P0 it documents the gap).

**Verify:** the good fixture, served by the task 6 static mount, shows a slider and a readout that changes when the slider moves (manual, recorded as a screenshot reference in the changelog).

## Task 6: Verification v0 (L0, render harness, mint, store, gate)

**Files:** `api/verify/{scan,render,mint,store,gate}.py`, `api/postprocess.py`, `api/static.py`, `api/verify/test_*.py`.

**Steps:**
1. Read the current Playwright (Python) docs. `uv add playwright` then `uv run playwright install chromium`. Record the download size and free disk after.
2. Port v3's post-processor rules (forbidden-API scan, single document, CSP injection naming `PUBLIC_ORIGIN`, size cap) with a provenance comment. Read v3's `evals/render_check.py` and port the assertions: `synapse_ready` within 5 s, no uncaught exception during a 10 s scripted interaction, every declared control causes an observable DOM change within 1 s.
3. Port the mint pattern from Arcana v2's `api/labs/verifier.py`: `VerifiedEnvironment` can only be created through a function holding a closure token; it cannot be subclassed or changed.
4. A SQLite store keyed by id with the HTML's SHA-256; an entry is never replaced. The gate re-reads the stored HTML, re-hashes it, re-runs the L0 scan, and only then builds the `EnvironmentBlock`.
5. Mount `/vendor/kit/<semver>/` as static files from the Kit's `dist`.

**Verify:** `uv run pytest api/verify -q` includes and passes:
- the good fixture is minted, stored, and the gate returns a block whose hash equals the stored hash;
- `reference-spring.bad-fetch.html` is refused at stage `scan`, naming the API;
- `reference-spring.bad-dead-control.html` is refused at stage `render`, naming the control;
- a stored HTML mutated by one byte is refused by the gate;
- a source-scan test: the mint issuer is referenced only in `api/verify/mint.py`, and `VerifiedEnvironment(` is not constructed anywhere else;
- the injected CSP string equals the expected string and names `PUBLIC_ORIGIN`.

## Task 7: API `/ask` on fakes

**Files:** `api/main.py`, `api/routes/ask.py`, `api/sse.py`, `api/routes/test_ask.py`.

**Steps:**
1. Read the current FastAPI streaming docs (rule 6).
2. `POST /ask {"question": "..."}` streams `meta` (lane `instantiate`, label `dev-fixture`), a few `text_delta` events from the fake explainer, an `environment` event built through the gate from the stored fixture, then `done`. `GET /health` returns 200.

**Verify:**
- `uv run pytest api/routes -q` parses the stream and asserts the order `meta`, `text_delta`+, `environment`, `done`, and that each event validates against the generated models.
- `curl -N -X POST http://localhost:8000/ask -H "content-type: application/json" -d '{"question":"why does a spring stretch"}'` prints those events in that order.

## Task 8: Web shell

**Files:** `web/` (a Next.js app), `web/lib/{stream,hash,sandbox}.ts`, `web/components/{EnvironmentFrame,Peek,Stage}.tsx`, `web/**/*.test.ts(x)`, a rewrite in the Next config proxying `/vendor/*` to the API.

**Steps:**
1. Read the current Next.js, React and Tailwind docs (rule 6). Do not copy configuration from memory.
2. Consume the SSE stream and validate each event against the generated types. Compute the HTML's SHA-256 with SubtleCrypto and refuse to render on a mismatch. Render in an iframe whose `sandbox` is the pinned constant `allow-scripts`.
3. Peek: one readout, one control, an Open action. Stage: full viewport with a back affordance. At most two actions in Peek.
4. Proxy `/vendor/*` to the API so the Kit is same-origin with the page (a v3 finding: a `srcdoc` iframe resolves relative URLs against the parent).

**Verify:**
- `pnpm --filter web test` passes: the sandbox constant equals `allow-scripts` exactly; a hash mismatch is refused; an unknown block type is ignored, not a crash.
- A real-browser smoke (Playwright): ask a question; the Peek appears; Open shows the Stage; moving the slider changes the readout; a `fetch` from inside the frame is blocked; `iframe.sandbox` is `allow-scripts`; the console has no errors. Record a screenshot reference.

## Task 9: Coverage census

**Files:** `data/kssm_topics.json` (ported), `eval/census/census.py`, `refdocs/evidence/README.md`, `refdocs/evidence/2026-10-16-p0-census.md`.

**Steps:**
1. Read the taxonomy (`kssm_topics.py` v3 in Synapse-V3) in full, including its page-citation comments. Port as data with a provenance note. It is topic names, chapter numbers and page numbers, not textbook text.
2. Write the criteria first, at the top of the census file: the allowed values and a one-line definition for each column.
   - `pattern`: simulation, virtual_experiment, explorable_diagram, process, data_viz, exam_practice, text_only
   - `model_kind`: closed_form, stepped, combinatorial, stochastic, process, qualitative, none
   - `kit_kinds_needed`: a subset of ui, scene, interaction, science, pedagogy
   - `expected_lane`: instantiate, compose, free
   - `confidence`: high, medium, low
3. Annotate all 53 rows with a one-line rationale each. Do not use a model; this is judgement.
4. Produce counts per subject and form, per pattern, per model kind and per expected lane, and a first ordering of science micro-models by how many topics each would serve.

**Verify:**
- `uv run python eval/census/census.py --check` exits 0: 53 rows, unique slugs, every cell in its allowed vocabulary, counts sum to 53.
- The owner has reviewed the table; the review is recorded in the changelog and a ledger row.

---

## Wrap-up (do not skip)

- [ ] `refdocs/STATUS.md`: phase table updated, verification ledger updated with what was actually run
- [ ] `refdocs/changelog/CHANGELOG.md`: session entry added
- [ ] `refdocs/changelog/DECISIONS.md`: any new ADR, any resolved `ASSUMED:`; D-09 resolved by the census
- [ ] PRD glossary: add the P0-only `dev-fixture` label, and note its removal in P1
- [ ] This doc updated to match what actually happened
- [ ] `refdocs/plans/README.md` and `refdocs/execution/README.md` index statuses updated
