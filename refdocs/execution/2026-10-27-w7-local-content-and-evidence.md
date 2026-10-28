# Execution: W7a, the local content and evidence batch

> Plan: `refdocs/plans/2026-10-27-w7-local-content-and-evidence.md`. Written and kept current while building (CLAUDE.md rule 4). Anything here marked "deviation" is where the build differed from the plan.

## Order of work (and why this order)

1. **Pull and set up** (done): fast-forward to `origin/main` 7fb56d8, `pnpm install --frozen-lockfile`, Kit build (hash `a60c334b3534`, as the previous session recorded), codegen check, `uv sync`, move the stale `data/environments.db` aside (`environments.db.pre-orbit-20261027`, not deleted), reseed.
2. **Corpus-bound evidence** (done): orbit pointers, printed pages, misconception source note. These come first because the plan-registry test and the library both depend on the orbit citation.
3. **Offline lab report and print** (done): shell panel in `api/export.py`, tests in `api/test_offline_lab.py`; web print button and stylesheet.
4. **Printed page through the wire** (done): schema, codegen, evidence code, both formatters, the web stream parser, tests.
5. **Ceiling, five models, four Plans** (done): `spec.ts` and the Python mirror first, then models, wiring, planted bugs, references, hand-worked rows, Plans, pointers, plan checks, then the real build with the corpus.
6. **Evidence sets** (done): reference fixtures (`eval/l6/make_fixture.py`), L6 rows, L4 regeneration, cost projection.
7. **Cache accounting** (done): pricing, ledger and migration, service, provider, factory, setting, tests.
8. **Kit wording** (done): the placeholder text and `cardiacOutput`.
9. **Review** (done): kit-guardian and cost-auditor, read-only; findings fixed with a test each (PLAN-021, the shell's closed flag, the sparse-array hole, printed page validation, the refraction index start, the half-life unit wording, the ledger migration race, the ignored store copy).
10. **Combined verification** (done, one test fixed on the way) and docs (done). Open: the browser smoke (port 8000 was held by a dev server I did not start). The one-piece suite rerun (1206 passed, 1 skipped) and the library reseed are done.

## Deviations from the plan

- **Unit label `s-1` became `/s`.** The verifier's copy-number rule reads the "1" in "s-1" as a number no control backs (`render/unbacked_copy_number`), so the half-life model's unit is `/s`, like the existing `/cm`. Found by the first real build, fixed in the Kit, the reference, the Plan and the manifest. The Kit was relocked again.
- **The L4 size test was pinned at 17 controls**, one per golden Plan at the time (orbit had not been added to the set). The test now says "one control per golden Plan", whatever their number; the set is regenerated at 57 cases (35 planted, 22 true).
- **An unplanned edit to a second inventory test** (`test_wording.py`, `len(PLANS) == 17`, now `>= 22`) and the golden-topic list in `test_plan.py`.
- **Two registry rules, then one.** The registry first required the printed page to be below the PDF page; an older synthetic test (page 2, printed page 27) broke it, so the registry checks "a positive whole number" and the committed-pointers test keeps the "small step below the PDF page" rule.
- **A tamper test of mine went stale.** `api/test_chapter_pack.py` edited the first "Voltage", which is now in the Kit script (the transformer model), so the Kit check failed instead of one Environment. It edits the last occurrence now (Environment data).
- **`CORPUS_DIR` changes the label tests.** Two tests in `api/routes/test_ask.py` expect no corpus (label `model-checked`); run the suite without `CORPUS_DIR` set, and set it only for `eval/environments/build.py` and the seeding command.
- **The first long Python run was invalid.** It overlapped a Kit rebuild and relock, so its browser failures were noise. The verification run is the one after the build block.

## Facts worth keeping

- The corpus: `C:\Users\User\synapse-corpus\text\*.jsonl` (one file per book; keys `page`, `text`), quotations in `...\text\citations.json` (outside the repository). `CORPUS_DIR` is not read from `.env` by the assistant (reading `.env` is denied); commands set it in the shell for that command only.
- Printed page offsets (PDF page minus printed page): Physics F4 5, Physics F5 9, Chemistry F4 10, Chemistry F5 8, Biology F4 5, Biology F5 9. In Chemistry F4 only one side of a spread prints a trustworthy number, so a pointer on the other side takes its printed page from the adjacent page. 33 of 34 pointers have one; `rate_avg` does not (neither neighbour confirms it).
- No KSSM textbook, English or Malay, Form 4 or 5, contains "cardiac output" or "stroke volume" (searched 2026-10-27).
- The planted-bug suite of each new model has 10 to 13 bugs; the L6 rows plant 16 more into the built Kit bundle (15 caught by the independent references, 1 by the dead-control check) and 4 neutral controls are accepted.

## Verification ledger for this block

See the 2026-10-27 row in `refdocs/STATUS.md` and the changelog entry of that date: Python 1206 passed 1 skipped (after the fixes; the first run's 3 failures are explained above), Kit 559, web 121, L6 190 of 195 with 0 of 20 false positives, hostile 20 of 20, 22 of 22 `kit-verified`, ruff and pyright clean. The browser smoke was not run.
