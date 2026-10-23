# Execution: W2, instant and free library hits

> Plan: `refdocs/plans/2026-10-23-w2-instant-library.md`. Written after the build; kept true to what happened (CLAUDE.md rule 4). No paid call is made by anything here.

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | Store: a topic index (`library_topics`), the written answer kept with a cached question (with migration for older stores), `ConflictingRecord` | `api/verify/store.py` | `test_run_library.py` store tests: old store migrated, unknown Environment refused, entries in a stable order | Done |
| 2 | One builder for hand-written Plans; a seeding command | `api/pipeline/library.py`, `api/library_seed.py`, `eval/environments/build.py` | `eval/environments/build.py --corpus ...` still 16 of 16 `kit-verified`; `python -m api.library_seed` built 16 Environments, 16 `kit-verified`, into a scratch data directory | Done |
| 3 | The orchestrator consults the library first; hits go through the gate | `api/pipeline/run.py` | Spy provider sees zero calls for a topic hit and for a repeat | Done |
| 4 | A page byte-identical to a stored one is delivered as the stored one | `api/pipeline/run.py`, `api/verify/store.py` | `test_run_library.py` | Done |
| 5 | Tests | `api/pipeline/test_run_library.py` | see the STATUS ledger row of 2026-10-23 | Done |

## Notes

- **Deviation:** the first build crashed the request when the generated page equalled a library page (the store refuses to replace a row). Found by my own tests; fixed in task 4.
- **Seeding is a deliberate step:** the API does not seed on start (it needs Chromium and about a minute). Run `uv run python -m api.library_seed` once per Kit build, with `CORPUS_DIR` set to get `kit-verified` labels.
- **Not done:** flag-evicts-and-writes-a-regression-eval; library coverage beyond the 16 hand-written Plans.
