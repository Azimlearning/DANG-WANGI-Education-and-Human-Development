# Execution: W19, the generation pipeline v2

> Plan: `refdocs/plans/2026-10-29-w19-generation-pipeline-v2.md`. Tests written with the code; one combined run at the end (the owner's cadence).

## Order of work (as done)

1. Kit science: `planet_gravity.ts`, `weight.ts`, nineteen planted bugs in `science.test.ts`; Python references in `api/verify/references.py`, cross-checked against published surface gravity to 1 percent.
2. Kit interaction: `slider` `words` and a value beside the name; `handles.ts` (`quiet`, `onSteps`, `dragAlong`); `graph.ts` bars for a choice and a point handle; `planets.ts`; the orbit launch arrow handle; apparatus grips quiet their control; i18n words; manifest entries; `planets.test.ts`.
3. Verifier: handle `host`, `box`, `origin` in the audit; `_drive_handles` drags in the handle's own box from its starting value; `_handle_problems` grounds graph, planets and orbit handles; `_corner_range` and `_scene_scale_problems` take every step of a choice control.
4. Plans: `surface: planets`, `fit`, `missing`; `PLAN-023`; model chaining in `plan_checks.py` (`_value`, `_controls_under`) and `assemble.py`; schema regenerated.
5. Evidence: three pointers on Form 4 Physics page 91 (printed 86), quotations added to the local corpus file outside the repository, all proved with `Corpus.verify_quote`.
6. Library: `data/plans/physics-f4-planet_gravity.json`; the reseed is English only (`--english-only`, the owner's call).
7. Pipeline: `LANE_PREFERENCE`, `free_leads`, Free first with the Kit Plan as fallback, stage notes in the pipeline's words; planner v9, free v4.
8. Wire and web: `PlanDraft.components`; the turn log; `BuildLog`, `BuildDetails`; strings in both languages.
9. L6: the planets fixture and seven rows; docs.

## Deviations and facts worth keeping

- The verifier refused the first planets page: "the test mass is too small to grab". It renders at 480 px, where the row is drawn at about 0.8 scale, so a 44-unit grip came out near 36 px. Grips enlarged (planets 27, graph point 24). A real catch, not a test artefact.
- The plan checks and the verifier both took every control at its maximum as a picture's peak. For a choice control that is the last choice (Neptune), not the largest value (Jupiter): both now evaluate every step of a choice control.
- A Plan could not chain models (inputs were controls or constants); the Kit and the verifier already followed nested chains, so only the plan checks and the assembler changed.
- The Hooke's law model gained the gravitation topic, so a spring balance can weigh a mass on a planet without PLAN-016.
- The worst planner request after v9 is 8701 tokens (cap 9500).
- D-73's hidden control card is superseded: a quiet control keeps its name and value and hides only its bar.
