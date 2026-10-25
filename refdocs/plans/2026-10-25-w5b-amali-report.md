# Plan: W5b, the Amali lab report from recorded rows (roadmap C2)

> Execution doc: `refdocs/execution/2026-10-25-w5b-amali-report.md`. Workstream W5 of `refdocs/plans/2026-10-22-completion-roadmap.md`; PRD P6 (Amali mode). English only (the owner said to skip Bahasa Melayu, 2026-10-25).

## Why this exists

The demo shows a lab report built from the rows a student records. Today the Kit's `table` keeps recorded rows inside the sandboxed frame and the host cannot see them: the roadmap's finding 7 ("no path from the table's recorded rows to the host"). The Amali card (`experiment`) and the steps (`stepper`) are also visible only inside the frame. Without a path out, no report, no export, and no way to keep a student's own results.

## What's already covered

| Need | Where |
|---|---|
| The bridge and its four public functions | `packages/kit/src/bridge.ts` |
| The table with Record and Clear, the experiment card, the stepper | `table.ts`, `experiment.ts`, `stepper.ts` |
| The host's strict parser for frame messages, and `e.source` checked against our own frame | `web/lib/sandbox.ts`, `web/components/EnvironmentFrame.tsx` |
| L0 forbids `postMessage` in page code | `api/verify/scan.py` |

## Scope

**In:**
1. A new bridge message, `synapse_lab`, sent only by Kit components: the experiment card's fields, the stepper's steps, and a full snapshot of the table (caption, columns, rows) at creation and after each Record or Clear. It is **not** added to the public `window.Synapse` surface, so page code cannot call it.
2. The host parses it strictly (counts, lengths, text only) and keeps the latest of each part per Environment.
3. A report panel in Stage: Aim, Hypothesis, variables, apparatus, procedure, the results table, and three boxes the student writes in (observations, discussion, conclusion). Copy as text, and Download as a text file. The student's own writing stays in the browser and is never sent anywhere.
4. A Kit relock (D-29 keeps 0.1.0 unreleased and relocked on every change).

**Out (and why):**
- Marking, grading or "AI feedback" on the written parts: no reviewed rubric exists, and a model-judged score is never a primary metric (hard constraint 9).
- A PDF or Word export: a text file is portable and has a plain text equivalent; a real format needs a library and a layout review.
- Storing a report on the server: no accounts (D-11); the report lives on the device.
- A report for the offline export and share-link pages: those have their own shells; later, once this is proved in Stage.

## Approach

- **The report is a view of what the Kit showed.** The host never composes experiment text of its own; the strings come from `own`ed Kit elements, so the same checks that verified the page cover them. The host still treats the message as untrusted text: it validates shape and sizes and renders it only as text.
- **Snapshots, not deltas.** Each table message carries all rows, so the host state is a replacement and a lost message cannot corrupt it.
- **Unreachable from page code.** The message function is exported from `bridge.ts` for the Kit's own modules and left out of `index.ts`; a Kit test asserts the public surface is unchanged, and another that a page cannot reach it.
- **Honest wording.** The panel says the rows are the ones the student recorded from the model, and that the written parts are the student's own and are not checked.

## Risks and unknowns

- **A Kit change touches the verifier's world.** The harness presses Record and Clear; a new outgoing message must not be mistaken for an event or a violation. Mitigation: Kit tests, the L6 run, the hostile set, and a `kit-guardian` review (the L6 baseline must not move).
- **Recorded values are formatted strings** (`toFixed`), so the report shows exactly what the student saw. Confidence: high.
- **Opaque origin.** The frame posts with target `*` (as the bridge already does); the host checks `e.source`. Same as every other bridge message.

## Definition of done

- A Kit test: Record posts a snapshot with the new row, Clear posts an empty one, the experiment and the steps post once, and `window.Synapse` has the same public surface as before.
- Host tests: the parser refuses oversized and non-string input; the panel renders a fixture and its text export is exactly the visible content.
- In the real-browser smoke at 360 px: record two rows in the Hooke Amali Environment and see both in the report, with no horizontal scroll and 44 px targets.
- L6 and the hostile set are unchanged, and the Kit is relocked.
