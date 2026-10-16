# Synapse v4: Claude Context

> Read this file at the start of every session, then run through `.claude/memory/preflight.md`, the six-question gate that turns these rules into something you actually did. Synapse v4 turns a Malaysian Form 4 or 5 KSSM science question into a verified, interactive **environment**: raw HTML/JS assembled over a vetted micro-component Kit, with the textbook evidence beside it.
> The PRD is the source of truth; this file is the short operating brief; preflight is the gate. Keep all three short.

---

## Order of authority (when docs conflict, surface it; don't resolve silently)

0. `refdocs/STATUS.md`: **where we are right now.** Phase checklist + the current phase's progress. Check this first, every session.
1. `refdocs/synapse-v4-PRD.md`: **what & why.** Owns scope, architecture, roadmap, Decision Log.
2. `refdocs/changelog/DECISIONS.md`: **settled calls.** Read before re-debating an architectural choice.
3. `refdocs/plans/*.md`: **what to build & why.**
4. `refdocs/execution/*.md`: **how & in what order.**
5. `refdocs/guides/`: **operational reference.** `env_setup.md` (every variable, where to get it), `checklist.md` (pre-ship).
6. `refdocs/synapse-v4-sources.md`: **raw research** (external references, repos, APIs, rejected options).
7. `refdocs/brainstorm-2026-10-16.md`: **founding context, historical.** Its Amendment A1 supersedes the sections it names. Where it disagrees with the PRD, the PRD wins.

If two docs disagree, stop and ask. Don't pick one and move on.

---

## Mandatory rules

### 1. Update the changelog after every session
After any session that changed code, made a decision, or modified a plan, add an entry to **`refdocs/changelog/CHANGELOG.md`** (format is in that file). Do not skip. Even a one-line fix gets a one-line entry.

### 2. Plan before you build
Before implementing any non-trivial feature, a **plan doc** (`refdocs/plans/`) and an **execution doc** (`refdocs/execution/`) must exist. If they don't, create them before writing code.

### 3. Log decisions as ADRs
New architectural/design decision: add an ADR to `refdocs/changelog/DECISIONS.md` (Decision, Why, Rejected/Trade-off). Mark unresolved assumptions `ASSUMED:` and surface them at the next checkpoint.

### 4. Keep docs current
If you deviate from a plan during execution, update the execution doc to match reality. Stale docs are worse than no docs.

### 5. Port with provenance
A file copied or adapted from Synapse v1/v2/v3 or Arcana v2 starts with a comment naming the source repo, path and commit. Read it fully and adapt it to this repo's interfaces; never paste and patch until it compiles.

### 6. Read current docs before using a library
FastAPI, Pydantic, Next.js, React, Playwright, esbuild, vitest and the provider SDKs have all changed since the code being ported was written. Read their current docs (context7 or official) before writing against them. Do not encode an API recalled from memory.

### 7. Prompts are files, and paid runs need the owner's go
Prompt packs live in `api/prompts/` as versioned files, never inline in Python strings. A change to a prompt records an eval delta (commit prefix `prompt:`). Any paid run (evaluation, ingestion, generation sweep) states a projected amount first and waits for the owner's confirmation. Fakes are the default.

### 8. Writing style
No em dashes and no en dashes in docs or user-facing text. Use commas, colons, new sentences, and "to" for ranges.

---

## The hard constraints (these are mechanism, not preference)

1. **No unverified Environment reaches the client.** The deliverable type can be minted only by the verifier module. The delivery gate re-derives the block from the stored record, re-hashes and re-checks it. The browser re-hashes before rendering.
2. **The sandbox is exact.** The artifact iframe is `sandbox="allow-scripts"` and nothing else, never `allow-same-origin`. The injected CSP names the configured public origin explicitly (an opaque-origin `srcdoc` makes `'self'` match nothing). No runtime CDN. Scripts load only from `/vendor/` and `/vendor/kit/<semver>/` on our own origin.
3. **Lanes and labels are honest.** A generated Environment is Instantiate, Compose or Free, decided by what verification it survives, and carries that lane's trust label in the UI. Free output is never `canonical` without human review, and every Free generation is logged as a Kit gap candidate.
4. **Ground before generating.** A `kit-verified` label requires a textbook citation (carried by the science micro-model or retrieved). Where no source exists the label says so and the output cannot rise above `model-checked`.
5. **Only the Composer places blocks.** The Composer chooses presentation (Peek, Stage, Companion, Shelf) and placement by deterministic rules. A block that fails validation is dropped, never repaired.
6. **Micro-components join on evidence.** A micro-component needs a written precondition, a signature in the Kit manifest, an accessibility fence and a registration suite that refuses every planted defect. A science micro-model also needs a textbook citation, units and domain, an independent hand-written reference and properties. A behaviour change bumps the Kit semver, which marks stored environments stale.
7. **The wire is typed once.** Every type that crosses the wire is defined in `packages/schema` and generated into Python. Strict models, fail closed.
8. **Spend is capped and governed.** Every paid call goes through the LLM seam and the spend ledger, and is refused before sending if it would exceed `LLM_MONTHLY_CAP_USD`. Fakes are the default. A paid run states its projected cost and waits for the owner.
9. **Evaluation protocol is fixed before runs.** Golden and hostile sets and their hashes are pinned; a change is a declared amendment. Model-judged scores are never the primary metric. The verifier's detection rate on planted physics bugs is reported, not assumed.
10. **Accessible and phone-first.** 360 px wide, 44 px touch targets, reduced motion respected, a text equivalent for every visual. Checked statically and in a real browser.
11. **Provenance is always visible.** The student sees the citation, the lane label, what was checked, and its limits.
12. **Single operator, do not expose.** There is no auth and no rate limit yet (ADR D-11). The API must not be reachable from the public internet until the deploy gate in `refdocs/guides/checklist.md` is met and recorded.
13. **Public-repo hygiene.** No secrets, no personal data, no textbook PDFs or extracted passages, no event admin material. This folder becomes its own repository.

---

## Stack

- **API (`api/`):** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy over SQLite for local stores, managed with **uv**. Playwright (Python) for the render and verification harness.
- **Web (`web/`):** Next.js, React, Tailwind, Vitest, managed with **pnpm**.
- **Kit (`packages/kit/`):** the micro-component library in TypeScript, built by esbuild into versioned static bundles, tested with Vitest.
- **Schema (`packages/schema/`):** TypeScript source of truth, codegen to Pydantic.
- **LLM:** Anthropic API primary, OpenRouter optional fallback, model tiers per task.
- **Retrieval:** BM25 or TF-IDF first; dense embeddings only if measured to help. No graph retrieval.

Exact versions are pinned in P0 task 1 (observed on the dev machine 2026-10-16: Python 3.13.14, uv 0.11.26, Node 24.11.0, pnpm 10.12.1).

## Surfaces

One product, four packages. They share source **only** through `packages/schema` (wire types) and the Kit manifest (a generated JSON catalogue of micro-components). A change to A does not change B until its generated artefact is rebuilt.

| Surface | Root | Run | Can | Cannot |
|---|---|---|---|---|
| API | `api/` | `uv run uvicorn api.main:app --reload` | Retrieval, planning, generation, verification, lifecycle, spend | Render UI |
| Web | `web/` | `pnpm --filter web dev` | Host the chat shell, present Environments in the sandbox, hash-check | Hold secrets, reason, call an LLM |
| Kit | `packages/kit/` | `pnpm --filter kit build` | Micro-components, built to `dist/<semver>/` and a manifest | Server logic, network |
| Schema | `packages/schema/` | `pnpm codegen` | Define wire types | Contain logic |

`api/` and `web/` never import each other. Generated Environment HTML reaches the Kit only as a script tag at `/vendor/kit/<semver>/`.

**Naming hazard.** "Environment" is the learner-facing artifact. Process settings are "settings" (the `.env` file). Never abbreviate the artifact to `env`.

## Running it

| What | Command | Notes |
|---|---|---|
| Install | `uv sync` and `pnpm install` | Created in P0 task 1 |
| API | `uv run uvicorn api.main:app --reload --port 8000` | Fakes by default (`SYNAPSE_LLM_MODE=fake`) |
| Web | `pnpm --filter web dev` | Reads `NEXT_PUBLIC_API_BASE_URL` |
| Kit | `pnpm --filter kit build` and `pnpm --filter kit test` | Builds `dist/<semver>/` and the manifest |
| Codegen | `pnpm codegen` and `pnpm codegen:check` | Run after any schema change |
| Tests | `uv run pytest` and `pnpm -r test` | |
| Lint and types | `uv run ruff check api`, `uv run pyright api`, `pnpm -r lint`, `pnpm -r typecheck` | |
| Evals | `uv run python eval/run.py` | Costs money in live mode; confirm first |

None of these exist until P0 task 1 creates them.

---

## Build sequence

**P0** walking skeleton and coverage census, **P1** Kit core and verification harness, **P2** evidence, **P3** the Mark 3 generation pipeline and the first vertical, **P4** Kit expansion by kit, **P5** library and lifecycle, **P6** pedagogy, **P7** reach and the deploy gate, **P8** evidence and learner study. Details: PRD section 6.

**Never build the second of anything until the first is green end-to-end.**

---

## When blocked

- **Open question:** check the PRD's Open Questions section. If unresolved, write your assumption to `DECISIONS.md` as `ASSUMED:`, proceed, surface at the next checkpoint.
- **Doc conflict:** stop. Quote both passages and ask. Don't pick silently.
- **Ambiguous spec:** prefer the safer, more verifiable, less-coupled option. Log the choice.

---

*Companion brief to `refdocs/synapse-v4-PRD.md`. Last updated: 2026-10-16.*
