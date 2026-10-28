# Execution: W12, Bahasa Melayu

> Plan: `refdocs/plans/2026-10-27-w12-bahasa-melayu.md`. Kept current while building (CLAUDE.md rule 4). Targeted tests only while building, one combined verification at the end (the owner's cadence of 2026-10-27).

## Order of work

1. **Kit i18n.** `packages/kit/src/i18n.ts` (table, `setLang`, `kt`); replace the fixed strings in `environment`, `table`, `hints`, `concept_check`, `predict_card`, `reset`, `worked_solution`, `experiment`, `graph`, `mass_hanger`, `valve`, the four scenes; export `setLang`; manifest entry; tests (every key has both languages; Malay differs from English; English output is byte-identical to before for an English page, so the existing Environments keep their hash). Relock.
2. **Overlay and assembler.** `api/i18n/overlay.py` (pointers of a Plan, load, check, apply), `assemble(..., lang=)` emitting `Synapse.setLang("ms")`; tests with planted defects.
3. **Builder and store.** `translations` table, `eval/environments/build.py --lang ms`, `library.seed` linking; API route and `BM_SHOW_DRAFTS`; schema type; codegen.
4. **Web.** `lib/i18n.ts`, the string tables, the switch, the fallback note, the draft mark; components read strings through `t()`.
5. **Drafts.** The web chrome strings; the overlays for 30 Plans (glossary first, then the four demo labs, then the rest).
6. **Review workflow.** Export and import script, tests.
7. **Verification and docs.**

## Deviations and facts worth keeping

- **The verifier read English.** The first full Malay build stopped at the titration: the eye check looked for the words "above", "level" and "below" in the Kit's sentence. It now reads them by the page's language (`EYE_WORDS`: "di atas", "adil", "di bawah"). No other check read a Kit word.
- **Order of the pieces.** Kit table and `lang` option first, then overlay and assembler, then the store and API, then the web, then the 30 drafts, then the review tools. 30 of 30 translations verified and `kit-verified` with the corpus.
- **Questions stay English.** The quick starts, the composer example and the routing are English; a Malay question gets the guard of W13 and an English written answer. The composer's Malay placeholder says so.
- **No `.env` change was made.** To see Malay drafts in a demo set `BM_SHOW_DRAFTS=true` for the API and `NEXT_PUBLIC_BM_DRAFTS=1` for the web build (both off by default); `.env.example` is blocked to my tools, so these two lines are for the owner to paste.
- **The reviewer's path.** `uv run python -m eval.i18n.tools sheet review.csv` (Plan strings) and, for the page's own words, `web/lib/strings.json` (flip `reviewed`); the Kit's fixed words are in `packages/kit/src/i18n.ts` and are reviewed together with the Plans (a Kit change bumps the lock).
