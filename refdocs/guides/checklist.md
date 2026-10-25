# Pre-Ship Checklist: Synapse v4

> Run the relevant section before pushing, deploying, or calling a phase done.
> Not every item applies to every change: use judgement based on what actually changed. But read the list; that's where you notice the thing you forgot.

---

## Every change

- [ ] **It was actually run.** Not "it compiles": executed, and the result observed. If it wasn't run, say so rather than implying otherwise.
- [ ] **Build passes:** `pnpm -r build` and `pnpm --filter kit build`
- [ ] **Tests pass:** `uv run pytest` and `pnpm -r test` (or: no test suite exists yet, which is a known gap in STATUS.md)
- [ ] **Lint and type check clean:** `uv run ruff check api`, `uv run pyright api`, `pnpm -r lint`, `pnpm -r typecheck`
- [ ] **No secrets staged:** `git status` shows no `.env*`; no key literal in the diff
- [ ] **No corpus staged:** no PDF, no extracted passage file, no textbook text (ADR D-14)
- [ ] **No stray debug output** left in the diff
- [ ] **Changelog entry added:** `refdocs/changelog/CHANGELOG.md`, including an honest **Verified** line
- [ ] **STATUS.md reflects reality:** the phase table doesn't round up, and the verification ledger has a row for what you just ran
- [ ] **Docs match what you built:** if the work diverged from the execution doc, that doc is edited, not left stale
- [ ] **No em dashes or en dashes** in any doc or user-facing string

Commands marked above do not exist until P0 task 1 creates them.

---

## New dependency

- [ ] Recorded in `refdocs/synapse-v4-sources.md` with its license and why it was chosen
- [ ] License is compatible with this project's distribution
- [ ] Its actual docs and types were read: the API was not recalled from memory
- [ ] Considered-and-rejected alternatives noted

---

## New environment variable (process setting)

- [ ] Added to `refdocs/guides/env_setup.md` with where to get it
- [ ] Added to `.env.example` with a blank or fake value
- [ ] Missing-variable case fails loudly at startup, naming the variable

---

## Architectural decision

- [ ] ADR in `refdocs/changelog/DECISIONS.md`: Decision, Why, Trade-offs and rejected
- [ ] Same id added to the PRD's section 7 Decision Log
- [ ] Any `ASSUMED:` it resolves is deleted from the assumptions list and from PRD section 8

---

## Before any paid run

- [ ] A projected amount was stated to the owner and confirmed
- [ ] The run goes through the LLM seam and is written to the spend ledger
- [ ] `LLM_MONTHLY_CAP_USD` is set and larger than the projection
- [ ] A smoke subset or a single item ran first (the harness is alive before committing to the full set)
- [ ] The evaluation protocol and question set were fixed before the run

---

## Before any public deploy (the deploy gate, ADR D-11)

All must be true and recorded in the changelog before a public URL exists.

- [ ] Per-session and per-day request limits exist and are tested (BUILT in part: a per-client-address per-minute limit, a cap on questions in flight, and since 2026-10-25 a per-client-address and an overall limit per UTC day (`DAILY_LIMIT_PER_CLIENT`, default 200; `DAILY_LIMIT_TOTAL`, default 0 = off, set it before any public deploy), all in-process per worker, `api/limits.py`; there are no accounts, so an address stands for a session; a multi-worker or proxied deploy needs the same limits at the proxy)
- [ ] A monthly spend cap is enforced at the LLM seam and a dashboard shows cost per student per week (BUILT in part: `GET /spend` shows the month's total, split by purpose and model; there are no student accounts, so no per-student view)
- [ ] Generated HTML is verified in a no-network container with resource limits (not `node:vm`)
- [ ] The Free lane policy is set and its trust label is shown to students (ADR D-07)
- [ ] The corpus position is confirmed with the owner of the textbooks, or only cited short quotes are shown (A-8)
- [ ] The name question is decided (A-14)
- [ ] `security-reviewer` agent has been added and run over the diff
- [ ] A license is chosen
- [ ] A real-browser pass at 360 px on an actual phone width

---

## Surface-specific checks

### Wire type change (`packages/schema`)

- [ ] The type was changed in `packages/schema` first
- [ ] `pnpm codegen` was run and `pnpm codegen:check` is clean
- [ ] The Python models are strict and fail closed; an unknown field is refused
- [ ] The web registry handles the new block type, with all render states

### Micro-component change (`packages/kit`)

- [ ] A written precondition and a manifest signature exist
- [ ] A one-line prompt-sized doc exists
- [ ] An accessibility fence exists (role, label, text equivalent) and a 360 px test passes
- [ ] The registration suite of planted defects refuses every defect
- [ ] **Science micro-model:** textbook citation with page, units and domain, an independent hand-written reference, properties, and a planted-bug suite
- [ ] A behaviour change bumped the Kit semver, and stored environments are marked stale
- [ ] `kit-guardian` was run over the diff

### Prompt pack change

- [ ] The change is a file under `api/prompts/` with its version bumped
- [ ] An eval delta (smoke subset before and after) is recorded
- [ ] No verifier check was weakened to make an item pass
