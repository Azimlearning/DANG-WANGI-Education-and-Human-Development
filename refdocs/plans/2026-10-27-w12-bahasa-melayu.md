# Plan: W12, Bahasa Melayu (backlog C4, G2)

> Written 2026-10-27. The owner lifted the "no Bahasa Melayu without a reviewer" hold on the same day ("u can develop the bahasa melayu if needed"). The rule that only reviewed strings ship (PRD A-13, the video spec) stays: what changes is that the mechanism and the drafts now exist, and a person's review is the only thing that makes a string public. Execution: `refdocs/execution/2026-10-27-w12-bahasa-melayu.md`. Decision: D-62.

## What and why

The demo video flips a lab to Bahasa Melayu with an EN|BM switch: the page chrome, the lab's title and its words. Malaysian students may study KSSM science in either language, so a verified lab that only speaks English reaches fewer of them.

## The design in one paragraph

A translation is **a second Environment**, not a text swap in the browser. A translation overlay (`data/i18n/ms/<plan id>.json`) holds the Bahasa Melayu for every sentence of a Plan. The builder applies it to the Plan, gets a Plan in Bahasa Melayu, and runs it through the same plan checks, the same assembler (with the Kit's fixed words in Bahasa Melayu), the same verifier, the same hash and the same delivery gate. So every guarantee of the English Environment holds for the Malay one: the numbers on the page are backed by controls, the science model values are compared with the reference, the sandbox is the same. The two Environments are linked in a `translations` table (decisions about stored rows, like the lifecycle table), each with a review status.

## Scope

**In**
1. The Kit's fixed words (Try this, Key idea, Record, Clear, Show a hint, scene sentences, aria names) in a table with English and Bahasa Melayu; `Synapse.setLang`.
2. The overlay format, its checks (every translatable string present, digits preserved, nothing extra), the application to a Plan, and the language option of the assembler.
3. The builder: `eval/environments/build.py --lang ms`, and the library seeding of the translations.
4. The store (`translations`), the API (`GET /library/{id}/translations`, and a setting `BM_SHOW_DRAFTS`, off by default), the wire type in `packages/schema`.
5. The web: a string table with a `reviewed` flag per string, an EN|BM switch in the top bar and in the lab frame header, the fallback note, a "draft translation" mark.
6. Drafts of the Bahasa Melayu for the web chrome and for the Plans, written by the build assistant, marked `draft`.
7. The review workflow: a script that exports a sheet for a fluent reviewer and imports the reviewed file, flipping `status` only with a reviewer's name and date.

**Out, and why**
- Machine translation inside the product: nothing is translated at run time. A string is either written and reviewed or it is not shown.
- Questions asked in Bahasa Melayu: the router is English only. Its retraining is the models track (W13), which needs a GPU and the owner's sign-in.
- The textbook quotations: the textbooks are English; a citation is shown as it is.

## Honesty rules

- A draft is never shown by default. With `BM_SHOW_DRAFTS` on (a demo or a review session) every Malay lab carries a visible "Draf terjemahan, belum disemak" mark.
- Where a string has no reviewed Malay the student sees English, with a short note saying so.
- The trust label of a Malay Environment is the English one's (same Plan, same checks, same citation). The label never claims the language was reviewed.

## Exit criteria

- All 30 Plans have a draft overlay; each builds, verifies in a real browser and is stored as a linked Malay Environment.
- A planted defect in an overlay (a changed digit, a missing sentence, an extra field) is refused by the overlay check.
- With drafts off, the API serves no Malay Environment and the web shows English with the note; with drafts on, the switch flips the lab and the chrome, and the mark is visible.
- The Kit test suite, the L6 baseline and the hostile set are unchanged in result.
