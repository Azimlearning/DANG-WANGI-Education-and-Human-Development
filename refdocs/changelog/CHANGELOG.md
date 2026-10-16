# Synapse v4: Changelog

> Mandatory session log. Add an entry after **every** session where code changed, a decision was made, or a plan was modified. Newest first. Even a one-line fix gets a one-line entry.

Entry format:
```
### YYYY-MM-DD: [short summary of session goal]
- **Changed:** what files/components were touched and why
- **Decided:** any architectural or design decisions and the reasoning
- **Deviations:** anything that differed from the plan, and why
- **Verified:** what was actually run, and the result (not "should work")
- **Known issues / next steps:** what was left open
```

Those five lines are the floor, not the ceiling. Add these when the session earns them:
- **Reported:** the symptom in the user's own words, before you knew the cause
- **Diagnosed:** what you found, and how you proved it: the reproduction, not the hypothesis
- **Trade-off:** what this change costs, and who it costs it to
- **Noted, not changed:** something you found and deliberately left alone

Rules that make this file worth keeping:
- **"Verified" means a command was run.** Name it and give the result. If nothing was run, write "nothing verified this session".
- **Deviations are the most valuable line.** A plan that changed silently is a plan nobody will trust next time.
- **Write what you learned, not what you touched.**
- Don't rewrite history. Corrections go in a new entry that references the old one.

---

## [Unreleased]

### 2026-10-16: P0 tasks 1 to 3 (workspace, wire schema and codegen, settings, fake LLM seam and spend ledger)
- **Changed:** Task 1: `pyproject.toml` (uv, Python 3.13, FastAPI, Pydantic 2, SQLAlchemy, pytest, ruff, pyright), `.python-version`, `package.json`, `pnpm-workspace.yaml`, `packages/schema` and `packages/kit` manifests, `uv.lock`, `pnpm-lock.yaml`, `api/`, `eval/` packages. Task 2: `packages/schema/src/{blocks,errors,events,index}.ts`, `packages/schema/codegen/to_python.ts` (ported from Arcana v2 `21c6dcf5`, provenance comment in the file), generated `api/schema/generated.py`, `api/schema/test_strict.py`. Task 3: `api/core/{settings,errors}.py`, `api/llm/{types,models,pricing,ledger,service,factory}.py`, `api/llm/providers/{base,fake}.py` (all ported or adapted from Arcana v2 `21c6dcf5` with provenance comments, each read in full first), `api/llm/test_service.py`, `api/conftest.py`.
- **Decided:** D-15 (live mode needs only an Anthropic key and a cap; no live provider exists until P3). Wire shapes: `EnvironmentBlock` carries `type` and `meta` in addition to the fields the execution doc listed; `ErrorCode` is `validation_failed | bad_request | not_found | spend_cap_exceeded | provider_unavailable | verification_refused | internal`.
- **Deviations:** (1) Rule 6 was only partly met: the docs sites (docs.astral.sh, pnpm.io) were unreachable from this container (DNS failure through the proxy), so config was written against the installed tools' own `--help` output (`uv init --help`, `pnpm help approve-builds`) and the working installs, not against the current online docs. (2) The toolchain here is not the Windows dev machine's: uv 0.11.32, Node 22.22.0, pnpm 10.28.0, Python 3.13.16 (STATUS recorded 0.11.26, 24.11.0, 10.12.1, 3.13.14); `packageManager` is pinned to pnpm 10.28.0. (3) Arcana v2 and GenUI-Education were attached as read-only shallow clones under `/home/user/azimlearning/` because the Windows source path does not exist in this container; Arcana v2 HEAD is exactly `21c6dcf5`. (4) `api/llm/fake.py` in the execution doc is `api/llm/providers/fake.py`, with `base.py`, `factory.py` and `models.py` added; per-turn `TokenBudget` and embeddings were not ported (not needed in P0). (5) Arcana's `test_codegen_guard.py` was not ported, so the `--src` and `--out` guard flags in the codegen are retained but untested. (6) `web/` is listed in `pnpm-workspace.yaml` but does not exist yet (task 8). (7) Ruff ignores E501 and excludes the generated file.
- **Verified:** `uv sync` exit 0; `uv run python -c "import fastapi, pydantic; print('ok')"` printed `ok`; `pnpm install` exit 0; `pnpm -r build` exit 0. `pnpm codegen` then `pnpm codegen:check` printed `codegen:check OK` (exit 0); renaming `planSummary` in `blocks.ts` without regenerating made `pnpm codegen:check` exit 1, and reverting it made it exit 0. `uv run pytest api -q`: 16 passed (6 in `api/schema`, 10 in `api/llm`), covering unknown field rejected, `"1"` rejected for an int field, unknown lane and label rejected, default mode fake with sockets blocked, live mode without `ANTHROPIC_API_KEY` naming it, without `LLM_MONTHLY_CAP_USD` naming it, a zero cap rejected, an over-cap request refused with the provider spy never called, spend accumulating toward the cap, a ledger row with purpose, tokens and cost. `uv run ruff check api`: all checks passed. `uv run pyright api`: 0 errors. Disk: 30 GB free before and after (9.3 to 9.4 GB used).
- **Known issues / next steps:** `pnpm -r test` was not run (the packages have no tests yet; vitest is set to pass with none). No clean-checkout rebuild was done. Pricing figures and model ids stay `ASSUMED` until checked against the provider pages before the first live call. Next: tasks 4 to 6 (Kit v0, reference Environment, verification), including a Playwright Chromium install whose download size must be recorded. No paid call ran and no real ledger row exists (tests use temporary ledgers).

### 2026-10-16: Project scaffolded
- **Changed:** Created the project doc system: `refdocs/` (PRD, STATUS, sources, guides/, changelog/DECISIONS, plans/, execution/), `CLAUDE.md`, `README.md`, `.gitignore`, `.env.example`, `.claude/` (settings, three agents, three commands, preflight, secret-guard hook). Wrote the founding brainstorm `refdocs/brainstorm-2026-10-16.md` with its Amendment A1. No application code yet.
- **Decided:** ADRs D-01 to D-14. In particular: "environment" is the artifact term (D-01); raw HTML/JS stays primary in three lanes (D-02); a Kit of hundreds of micro-components is an allowed building block (D-03); the Mark 3 pipeline is prompt packs plus the Kit plus accelerators (D-04); Python API + Next.js + schema + JS Kit (D-05, the agent's call as delegated); fakes by default and the owner confirms paid runs (D-08); no auth and no rate limit, so no public exposure until a deploy gate (D-11).
- **Deviations:** The founding brainstorm first recommended a data-first design with raw HTML only at authoring time. The owner rejected that in the interview; the brainstorm carries an amendment that supersedes the conflicting sections, and the PRD reflects the owner's choice. No parity doc and no file-structure doc were written (see STATUS Known gaps).
- **Verified:** Toolchain versions only (`uv --version`, `node --version`, `pnpm --version`, `python --version`, `git --version`, `df -h`); see STATUS verification ledger. Nothing else to verify: no code exists.
- **Known issues / next steps:** Eighteen `ASSUMED:` items are open (PRD section 8), the load-bearing ones being the oracle (A-5), the Kit API and size (A-2), isolation (A-10), exposure reading (A-11) and corpus legality (A-8). Next session starts from `refdocs/plans/2026-10-16-p0-walking-skeleton-census.md`.
