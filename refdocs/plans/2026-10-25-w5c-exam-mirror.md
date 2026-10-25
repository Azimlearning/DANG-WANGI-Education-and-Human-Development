# Plan: W5c, the exam mirror (roadmap C3)

> Execution doc: `refdocs/execution/2026-10-25-w5c-exam-mirror.md`. Workstream W5 of `refdocs/plans/2026-10-22-completion-roadmap.md`; PRD P6. English only (the owner said to skip Bahasa Melayu, 2026-10-25). The roadmap says "design first; no design exists": this is the design.

## Why this exists

The demo shows an exam-mirror answer scored "X of Y marks". A KSSM student is judged by SPM-style structured questions where each mark is one stated point, so the useful practice after exploring a model is to answer such a question and see which marking points the answer earned. Today nothing in the product does that.

## What's already covered

| Need | Where |
|---|---|
| The topic of a question, from the local router | `api/routing/router.py`, `api/pipeline/run.py` |
| A strict loader pattern and an optional stream event for host text | W5a: `api/models/probes.py`, the `probe` event, `web/components/ProbeCard.tsx` |
| Device-local progress | `web/lib/progress.ts` (D-33) |

## Scope

**In:**
1. `data/exam_items.json`: six hand-written structured questions (stem, total marks, one marking point per mark, a sample answer) for topics the Kit already covers. Each marking point lists the wordings that earn it.
2. A strict server loader and an optional `exam` stream event sent after the answer when the question's topic has an item and the turn did not fail.
3. **Marking is deterministic and runs in the browser:** a point is earned when the answer contains every word-stem of at least one listed wording. No model is involved and nothing the student writes leaves the browser.
4. A card: the question and its marks, a text box, "Mark my answer", then "X of Y marks" with each point shown as earned or missed in words, and the sample answer.

**Out (and why):**
- A model marking free text: a model-judged score is never a primary metric (hard constraint 9) and would cost money per answer.
- Marks for working or units in calculations: the first set is explanation questions.
- A bank of past-paper questions: copyright; every item here is original wording of a standard idea.
- Difficulty levels and spaced repetition: not scheduled (D-39).
- Saving scores: no accounts (D-11); device-local progress only, and only if it is cheap. Not in this step.

## Approach

- **Honest about what keyword marking is.** The card says: "Marked by matching key words, not by a teacher. A correct answer in different words can lose a mark." The score is a practice aid, never a result.
- **Same answer, same score.** The matcher is a pure function with tests, so a regression in the marking breaks a test, not a student.
- **Fail closed.** The loader refuses an item with no points, points that do not sum to the marks, an empty wording, a dash character, or a topic the router does not know.
- **Stems, not exact words.** A crude suffix strip makes "doubles", "doubled" and "doubling" match; the same rule applies to the answer and to the wordings.

## Risks and unknowns

- **The science and the mark points are the assistant's own and unreviewed.** A teacher must read them (A6). The card says so. Confidence for the six standard ideas: high; for mark-scheme fit to what SPM examiners accept: unknown.
- **Keyword marking is gameable and brittle.** Writing every keyword earns the mark with no understanding; a synonym can lose one. Mitigated by wording lists that need several stems together, by the honest note, and by never presenting the score as a grade. Not solved.
- **Wide topics.** `chemistry_form4_acids_bases_salts` covers titration, dilution and pH; the item is about neutralisation only. The item states its own scope in the stem.

## Definition of done

- The loader breaks on each planted fault (points not summing, empty wording, dash, unknown topic).
- The marker earns each point for its listed wordings, does not earn it for a related but wrong answer, gives the same score for the same text, and never awards more than the total.
- A question on a topic with an item gets one `exam` event before `done`; others do not; a refused or failed turn gets none; no model call is added.
- The card works at 360 px in the real-browser smoke with 44 px targets and its verdict in words.
