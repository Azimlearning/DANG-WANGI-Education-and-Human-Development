# Execution: W15, illustrated scenes

> Plan: `refdocs/plans/2026-10-28-w15-illustrated-scenes.md`.

## Order of work (as it happened)

1. **Refraction** (done): `packages/kit/src/refraction_scene.ts` (a degree control and `physics.refraction_angle` fed by it; incident and refracted rays from the normal; words: straight on, no bending, bends towards the normal), words in `i18n.ts`, manifest, `refraction.test.ts`; `SceneSpec.kind` `refraction` with a `model`; PLAN-019 rules (a deg control within 0 to 90, the model fed by it, `full` 90); the assembler; `provenance._refraction_problems`; the Plan; `test_plan_refraction.py`; three L6 rows and a regenerated fixture.
2. **Pressure** (done): `pressure_scene.ts` (the model's output in Pa against `full`; a probe and four arrows), words, manifest, `pressure.test.ts`; `SceneSpec.kind` `pressure` on the generic model-output path; the assembler; the Plan (`full` 200000 Pa for a 196 200 Pa reach); `test_plan_pressure.py`; three L6 rows and a new fixture `reference-pressurescene`.
3. **Verification and docs.**

## Deviations and facts worth keeping

- **Docs after code.** Rule 2 asks for the plan and execution docs before a non-trivial feature; these were written after the first two scenes were built and tested. Recorded here rather than back-dated.
- **No arrow markers.** The pressure arrows draw their heads inside the path: an SVG marker needs a `url(#id)` reference, which the Kit's audit and the planner rules treat as a URL.
- **A Kit-internal drawing bug is the registration suite's to catch.** An L6 row that made the Kit draw the refracted ray at the angle of incidence would be invisible to the runtime verifier (the scene checks itself against its own geometry), so it was not added; `refraction.test.ts` measures the drawn angles against the model instead.
- **The plan schema changed** (`api/prompts/schemas/plan.schema.json`, two new scene kinds), so the planner's request changed: no eval delta yet (paid, W8).
- The review run first failed because the web build on disk was the smoke's (its API port, 8011); the review builds its own.
