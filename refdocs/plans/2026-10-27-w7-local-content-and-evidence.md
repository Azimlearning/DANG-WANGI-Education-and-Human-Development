# Plan: W7a, the local content and evidence batch (everything the corpus unlocks, plus the free engineering left over)

> Execution doc: `refdocs/execution/2026-10-27-w7-local-content-and-evidence.md`. Workstreams W5 to W7 of `refdocs/plans/2026-10-22-completion-roadmap.md`. The owner told the local session (2026-10-27) to keep building until everything that can be built is built, to decide and record its own decisions, and to batch testing at the end. Paid runs are NOT part of this plan: CLAUDE.md rule 7 and hard constraint 8 still need the owner's go and a projected amount for each, and a general "carry on" is not that.

## Why this exists

The cloud session stopped at everything that needed the textbook corpus, the owner's machine or money. This session runs on the owner's machine, where the corpus is at `C:\Users\User\synapse-corpus`, so the corpus-bound items can be done, together with the free engineering the cloud session listed ("What I can still build here" in its last message and `refdocs/guides/remaining_work.md`).

## Scope

**In** (each is a numbered ADR in `refdocs/changelog/DECISIONS.md`, D-54 onwards):
1. **Orbit bench citations.** Four pointers for the three orbit models from the Physics Form 4 gravitation pages; the bench goes from `model-checked` to `kit-verified` (the plan-registry test already demanded a citation for every Plan).
2. **Printed page numbers.** Each pointer carries the book's own page number where the page or its neighbours show it; the wire type `Citation` gains an optional `printedPage`; the student reads "page 107 (PDF page 112)".
3. **Misconception sources.** What can be checked about the five bibliographic references without a library: do the papers exist, do they concern that misconception. `source_verified` stays false because nobody has read them.
4. **The lab report beyond Stage.** The offline single file and the chapter pack get the same report panel (built from the Kit's `synapse_lab` messages, re-validated in the file's own shell); the web report gets "Print or save as PDF" through the browser's print dialog and a print stylesheet. The share-link page already shows it (it uses Stage).
5. **More Environments by measured gap.** Four new golden Plans over four topics that had none (light and optics, heat, electromagnetism, nuclear physics), from five new science models: refraction angle, critical angle, specific heat capacity (SI), ideal transformer voltage, half-life decay. A model quantity may now have a ceiling (`max`), which refraction needs (an incidence angle must stay below 90 degrees); plan checks enforce it on controls, constants and parameters.
6. **Evidence sets follow the content.** New reference fixtures and 16 planted-defect rows plus 4 neutral controls for L6; the pinned L4 case set is regenerated (a declared amendment, no paid run has used it); cost projection regenerated.
7. **Prompt caching, ledger side (B6).** Cache read and write tokens are priced and booked; the Anthropic provider can mark the system prompt cacheable; a setting, off by default, turns it on. Measuring the saving is the one paid step and waits for the owner.
8. **Kit manifest wording (B3).** The per-model `citation` placeholder no longer claims the corpus is "not loaded until P2"; `cardiacOutput` says plainly that no textbook states it.
9. **Independent review** of the new trust-bearing code (kit-guardian over the Kit, shell and schema; cost-auditor over the money path), and the fixes it finds.

**Out (and why):**
- Any paid run (D1, D2, the L4 and Free canaries, the 24-question planner run): needs a projected amount and the owner's go.
- Bahasa Melayu: the owner said English only (2026-10-25).
- OCR of the five scanned Chemistry experiment books: needs an OCR tool installed on the owner's machine; recorded as the next local step, not a blocker for anything else.
- The MCP-Apps-shaped bridge (C5, second half): no consumer exists and the owner said "if you still want it"; building a protocol shim with nothing to talk to would be unverifiable.
- Deploy-gate items that need the owner (name, licence, host, signing key, Kit release) and `.env.example` (the permission settings deny the tools access to it).
- A teacher's review, a real-phone and screen-reader pass, the learner study: people.

## Approach

- One build block, then one combined verification run (the owner's batching rule): Kit tests, web tests, the whole Python suite, the browser smoke, L6, the hostile set, lint and types.
- Every number in a Plan's prose must be backed by a control, constant or parameter (the copy-number rule); derived answers are not stated, they are read off the model.
- Citations: quotations are verified word for word against the real page before a pointer is written; the quotation file stays outside the repository (hard constraint 13); pointer claims are short notes in our own words.
- A new science model needs the full registration set (hard constraint 6): units and domain, an independent hand-written reference, properties, and a planted-bug suite that refuses every defect.

## Risks and unknowns

- **The Kit is relocked several times** (0.1.0 is unreleased, D-29). Every stored or seeded Environment is stale after this session until the library is reseeded; the old local store was moved aside, not deleted.
- **The ceiling is a framework change** that touches three places (TypeScript spec, manifest reader, plan checks). A bug there could let a control reach a physically meaningless value; the new model's browser run and a planted-ceiling test are the guard, and the Kit review is asked to attack it.
- **The half-life rule is stated by the book for whole numbers of half-lives.** The model is the continuous exponential; the Plan keeps the time control on whole multiples. A different Plan using the model could show non-integer half-lives; the manifest precondition says to keep to whole multiples. `ASSUMED`: that is enough until a plan check can express "whole number of half-lives".
- **The cache write multiplier (1.25) is `ASSUMED`.** A higher assumed figure only makes the ledger more cautious.
- **The textbook pages were read by the assistant, not a teacher.** `checked_by` on every pointer says so.

## Exit criteria

All of the in-scope items built and verified in the combined run, the review findings answered, and the docs (CHANGELOG, STATUS, DECISIONS, remaining_work) brought to match.
