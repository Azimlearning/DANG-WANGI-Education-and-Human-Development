# Execution: W7b, five more models and the lab anatomy

> Plan: `refdocs/plans/2026-10-27-w7b-models-and-lab-anatomy.md`. Kept current while building (CLAUDE.md rule 4).

## Order of work

1. **Models** (done, two batches of five and three): specs, planted bugs and index/manifest wiring generated from one table (the generator scripts were in the session scratchpad and are not kept), independent Python references, hand-worked and refusal rows, pointers and quotations, Plans, L6 rows and fixtures.
2. **Content** (done): six exam items with vectors in both markers, hints on 26 Plans (two Plans are at the PLAN-010 word budget and have none), the lab report wording, the quick starts.
3. **Name matching** (done): `library.match_by_name`, `store.all_topic_entries`, the fallback in `_from_library`, tests.
4. **Kit anatomy** (done): `environment()` header, `main`, `panel`, `extras`; parts re-targeted (steps to the head, table and study sentences to the panel, predict, Amali, hints, check and worked solution to the extras); stylesheet; manifest text; assembler header line; scene before graphs in both skeletons; Kit relocked.
5. **Web** (done): takeover grid, `LabFrame`, progress menu in the top bar, Stage can open presenting, one title (Peek too), Composer overflow, disabled button contrast, the mass tray on the bench; tests; the smoke gained the visual-standard checks.
6. **Verification** (done, see below), then docs (this file, the ADRs, the changelog, STATUS).

## Deviations and facts worth keeping

- The first generator run stopped halfway (a quotation did not match across a line break); the script was made resumable and the quotation matcher tolerant of any run of whitespace.
- The corpus pages keep line breaks inside sentences and a broken "fi xed"; quotations are cut from the page text by pattern, never typed.
- The smoke's ports were fixed at 8000 and 3000, and a `uvicorn --reload` dev server I did not start holds 8000. The smoke now reads `SMOKE_API_PORT` and `SMOKE_WEB_PORT` (default the old ones) and passes the API address to the web build; it was run on 8011 and 3011.
- The progress check in the smoke follows the move of "My progress" to the top bar.
- A `kit-guardian` pass over the Kit and web changes was not run (agents start only on the owner's ask); the Kit tests (636) and the verifier (27 Environments, L6, hostile) did run.
- Reference fixtures were regenerated from their Plans for the anatomy change (the new ones, orbit and fermentation); the older hand-made fixtures (spring, ohm, pressure, titration, masses and the bad-* pages) were left as they were and still pass.

## Verification ledger for this block

See the 2026-10-27 W7b row in `refdocs/STATUS.md` and the changelog entry: Python 1302 passed, 1 skipped (one run, after the last code change); Kit 681; web 127; the smoke 59 of 59 (on ports 8011 and 3011); L6 206 of 211 refused, 0 of 28 false positives, no surprise miss; hostile 20 of 20; 30 of 30 Environments `kit-verified`; ruff, pyright, codegen, typecheck clean.
