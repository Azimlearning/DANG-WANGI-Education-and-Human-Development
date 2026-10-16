# Execution: P2, P5 and P6 cloud scope

> Plan: `refdocs/plans/2026-10-16-p2-p5-p6-evidence-library-pedagogy.md`. Written after the build; this is the as-built record.

## As built

**P2 evidence** (`api/evidence/`): `corpus.py` (load jsonl documents from `CORPUS_DIR` (`Settings.corpus_dir`), normalise, BM25 search, `verify(citation)` by exact match after normalisation), `citations.py`, `ingest.py` (local tool: text in, jsonl out), `catalogue.py` and `data/experiments/catalogue.json` (id, subject, form, topic, aim, source, status, models, plan id, `confirmed_by_person`). `api/app.py:evidence_for(settings)` returns `None` when no corpus is configured, so the best label is then `model-checked` (D-21, D-25). Tests use a synthetic corpus built in the test.

**P5 library and lifecycle** (`api/verify/store.py`, `gate.py`, `api/app.py`, `api/pipeline/run.py`): `lifecycle`, `flags` and `questions` tables; `status`, `withdraw`, `restore`, `flag`, `library()`, `remember_question`, `lookup_question`; the gate raises `withdrawn`; endpoints `GET /library`, `GET /library/{id}` and `POST` flag, withdraw and restore; the pipeline checks the cache first and falls through if the gate refuses the row.

**P6 pedagogy**: Kit `hints.ts`, `concept_check.ts`, `predict_card.ts`, `worked_solution.ts`; Plan fields `predict`, `hints`, `concept_check`, `worked_solution`; plan checks (components exist, copy numbers are backed, PLAN-013 for an out-of-range `correct`); assembler slots `predict`, `hints`, `check`, `worked` in both skeletons.

**Seam hardening** (`api/llm/service.py`, `providers/base.py`, `core/errors.py`, `core/settings.py`): see CHANGELOG.

## Verify

`uv run pytest api/evidence api/verify api/llm api/routes -q`; `pnpm --filter kit test`; `uv run python eval/environments/build.py`.

## Open

- A real corpus has never been loaded. The synthetic one proves the mechanism only.
- The `kit-verified` rule is unused in practice until the owner ingests textbook text locally.
- The pedagogy copy in the golden plans is the author's wording.
