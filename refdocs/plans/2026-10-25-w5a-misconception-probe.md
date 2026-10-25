# Plan: W5a, the misconception probe (roadmap C1)

> Execution doc: `refdocs/execution/2026-10-25-w5a-misconception-probe.md`. Workstream W5 of `refdocs/plans/2026-10-22-completion-roadmap.md`; PRD P6. The owner said to skip Bahasa Melayu (2026-10-25), so the probe is English only.

## Why this exists

The misconception matcher is a topic detector: it fires on 17 of 30 questions that state no misconception (`refdocs/evidence/2026-10-18-p1b-misconception-matcher.md`), so it must never be shown to a student as a diagnosis. Its own docstring says what a match is good for: "a reason to offer a probe question (P6)". Today a match only changes one line of the explain prompt. The PRD's P6 success bar is a misconception follow-up end to end: a probe, a correction and a check.

## What's already covered

| Need | Where |
|---|---|
| The matcher and its five entries (statement, correct, source, `source_verified: false`) | `api/models/misconceptions.py`, `data/misconceptions.json` |
| A labelled probe set and a threshold sweep | `eval/models/misconception_eval.py`, `misconception_probe.json` |
| Where the stream ends and the shell renders a turn | `api/pipeline/run.py` `run()`, `web/lib/turns.ts`, `web/components/MessageList.tsx` |

## Scope

**In:**
1. A hand-written probe for each of the five listed misconceptions (osmosis, Newton's first law, ionic versus covalent bonding, food from the soil, current used up; the first three were built first): one question, three or four options, the correct one, and a plain correction. Stored in `data/probes.json`, loaded and checked strictly.
2. A new wire event `probe`, sent just before `done` when the question matches a flagship entry at or above a measured threshold.
3. A card under the written answer: the question, the options, a verdict on the first answer, the correction, and the provenance of that correction (what it rests on and that it has not been checked by a person).
4. The threshold chosen from the existing sweep and recorded with its false-positive rate.

**Out (and why):**
- Any claim that the student holds the misconception. The card is worded as a question about an idea, never as "you think".
- Adaptive follow-up, spaced practice and difficulty levels: scheduled nowhere (D-39 out of scope).
- Progress counters for the probe: the existing device-local progress (D-33) stays as it is.

## Approach

- **A probe is host UI, not an Environment.** It is plain text rendered by React (escaped), never HTML from a model, so it needs no verifier and cannot weaken hard constraint 1. It carries its own honest label: the correction rests on the entry's recorded reference, which has `source_verified: false`, and no person has reviewed the wording.
- **Fail closed.** `data/probes.json` is validated at load: every probe names an existing entry, has two to four options, a valid `correct` index, no dash characters, and a source status copied from the entry rather than typed. A bad file stops the API at start, not at a student's question.
- **The probe event is optional on the wire** (a client that does not know it ignores it). Strict types come from `packages/schema` and are generated into Python (hard constraint 7).
- **Threshold.** Chosen from the sweep, restricted to the entries that have probes; reported with its false positives on the 30 quiet questions.

## Risks and unknowns

- **The wording is science content written by the assistant.** Confidence in the three corrections: high for Newton's first law and osmosis, medium for the bonding wording; no textbook page was read here (no corpus in the cloud). It is labelled as unchecked, and A6 (a teacher) is the real fix.
- **A probe on an unrelated question is noise.** Mitigated by the threshold and by making the card dismissible and clearly optional. Measured on the same-author probe set only, so the false-positive rate is a plausible reading, not a student rate.
- **Fixed answer position leaks the answer.** The correct option's position varies across the three probes, and a test asserts it.

## Definition of done

- `data/probes.json` loads, and a test breaks on each planted fault (unknown entry, bad index, one option, a dash).
- A question stating a flagship misconception gets a `probe` event before `done`; a neutral question and a degraded turn do not (unless it matches), and no model call is added (spy provider).
- The card renders in jsdom with the verdict logic tested, and in the real-browser smoke at 360 px with 44 px targets.
- Schema codegen is current; the CHANGELOG, STATUS and ADR record the threshold and the labels.
