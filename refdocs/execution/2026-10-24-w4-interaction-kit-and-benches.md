# Execution: W4 stages 1 to 3, the Hooke mass bench, the titration bench and the fermentation bench

> Plan: `refdocs/plans/2026-10-24-w4-interaction-kit-and-benches.md`. Written after the build; kept true to what happened (CLAUDE.md rule 4). No paid call is made by anything here.

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | `massHanger`, `springScene`, slider `snap`, styles, manifest entries | `packages/kit/src/{mass_hanger,scene,slider,style,index,manifest}.ts` | Kit tests (`mass_hanger.test.ts`, `kit.test.ts` public surface) | Done |
| 2 | The audit's `widgets` report and the runtime self-check | `packages/kit/src/{provenance,audit}.ts` | Kit tests | Done |
| 3 | Plan fields, checks PLAN-018 and PLAN-019, assembler, skeleton slot, regenerated planner schema | `api/pipeline/{plan,plan_checks,assemble,failchecks}.py`, both skeletons, `api/prompts/schemas/plan.schema.json` | `test_plan_masses.py`, `test_plan.py` | Done |
| 4 | The Hooke Plan on masses and a scene | `data/plans/physics-f5-hookes_amali.json` | environments build: 16 of 16 `kit-verified` | Done |
| 5 | L1 rules for widgets; the harness drives every mass, the keyboard and a finger | `api/verify/{provenance,render}.py`, `failchecks.py` (L1-022, L1-023, L2-006) | `test_drag.py`, `test_provenance.py` | Done |
| 6 | Planted defects | `eval/l6/{mutations,run}.py`, `data/fixtures/envs/reference-masses.*` | L6 | Done |
| 7 | Planner request back under the cap: schema injected compact | `api/pipeline/prompts.py`, `test_prompts.py` | `eval/cost/project.py` regenerated | Done |
| 8 | Relock the Kit (twice: after the first review's fixes, then after the second's) | `packages/kit/kit-lock.json` | build hash `645165be2121` | Done |
| 9 | Second-review answers: layout half of the widget report, captions owned, scene chain and scale in the verifier, every mass by keyboard and finger, planner pack v3, 12 more L6 rows | `dom.ts`, `provenance.ts`, `audit.ts`, `mass_hanger.ts`, `scene.ts`, `api/verify/{provenance,render}.py`, `api/prompts/planner.v3.md`, `eval/l6` | L6 84 of 90 refused, 0 of 14 false positives | Done |

## Verification (one batch, run 2026-10-24)

`pnpm --filter @synapse/kit build --relock`; `pnpm --filter @synapse/kit test` (364); `pnpm -r typecheck`; `uv run ruff check api eval`; `uv run pyright api eval` (0 errors); `uv run pytest -q` (868 passed, 1 skipped, on the final tree; an earlier full run had 1 failure, PLAN-018 reporting a start outside the range that PLAN-014 already reports, fixed); `eval/l6/run.py` (84 of 90 refused, 0 of 14 false positives, no surprise misses; the 6 misses are all recorded); `eval/hostile/run.py` (20 of 20); `eval/environments/build.py --corpus ...` (16 of 16 `kit-verified`); `eval/smoke/web_smoke.py --no-build` (27 of 27); `eval/cost/project.py` regenerated; screenshots of the bench at 360 px light and dark looked at.

## Notes

- **Deviations from the first build:** the first review found the scene accepted any Kit observable, the hung-mass count was an unchecked visual, the harness found masses by page-mutable markers and dragged only Mass A with the mouse, off-step values were not enforced, `full` was unbounded, and a Playwright error was reported as `drag_dead`. All were fixed (widgets report, snap, harness rewrite, PLAN-019 scale, harness error). The planner request exceeded the 7000-token cap after the schema grew, so the schema is injected compact.
- **My own test mistakes fixed:** the tray comes before the hanger in document order (tests now sort the masses by letter); PLAN-018 reported twice for a start outside the range (now left to PLAN-014).
- **After this work every stored or seeded Environment is stale** (the Kit's bytes changed, D-16): re-run `uv run python -m api.library_seed`.
- **Not done:** stages 2 to 4; a real phone; a screen-reader pass of the live region; a paid planner canary (W8).


## Stage 2: the titration bench (2026-10-25)

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | The end-point model, with its registration suite, independent reference and pointers | `packages/kit/src/science/titration_endpoint.ts`, `science.test.ts`, `api/verify/references.py`, `data/citations/pointers.json` | 11 planted bugs refused; the two models are each other's inverse | Done |
| 2 | `valve` and `titrationScene` (burette, flask, eye) | `valve.ts`, `titration_scene.ts`, `parts.ts`, `style.ts`, `manifest.ts`, `index.ts` | `valve.test.ts` | Done |
| 3 | Plan fields, PLAN-018 for valves, PLAN-019 for titration scenes, assembler | `plan.py`, `plan_checks.py`, `assemble.py`, `failchecks.py` | `test_plan_titration.py` | Done |
| 4 | The titration Plan rewritten, the eye-level citation | `data/plans/chemistry-f4-titration.json`, `pointers.json`, the local corpus quotation file | 16 of 16 `kit-verified` | Done |
| 5 | The verifier holds the scene to the plan; the harness drives every valve and the eye | `api/verify/{provenance,render}.py` | `test_gestures.py` | Done |
| 6 | Second-review answers: no page CSS, guarded parts, derived end point, scoped eye lookup, wording, planner pack v4 | `audit.ts`, `dom.ts`, `provenance.ts`, `environment.ts`, `watch.ts`, `parts.ts`, `plan_checks.py`, `provenance.py`, `render.py`, `planner.v4.md` | L6, gesture tests | Done |
| 7 | Planted defects | `eval/l6/mutations.py`, `data/fixtures/envs/reference-titration.*` | L6 | Done |
| 8 | Relock the Kit | `packages/kit/kit-lock.json` | build hash `79974807fd91` | Done |

**Verification (run 2026-10-25):** `pnpm --filter @synapse/kit test` (393); `pnpm -r typecheck`; `uv run ruff check api eval`; `uv run pyright api eval`; `uv run pytest -q` (938 passed, 1 skipped); `eval/l6/run.py` (127 of 132 refused, 0 of 15 false positives, no surprise misses); `eval/hostile/run.py`; `eval/environments/build.py --corpus ...` (16 of 16 `kit-verified`); `eval/smoke/web_smoke.py --no-build`; `eval/cost/project.py` regenerated; screenshots of the bench in use at 360 px, light and dark, looked at.

**Notes.** The first build was refused by its own reviewer in three ways (12 attacks minted, 3 valid benches refused, V3's parallax wording backwards); the answers are in D-45. My own test mistakes fixed: a pointer drag in jsdom must use the element's own rectangle (the audit's reads go through captured primitives, which a test cannot patch); the valve's status sentence did not follow the control; the eye drag in my screenshot script needed the eye scrolled into view. **Not done:** stages 3 and 4; a screen-reader pass of the eye and the stopcock; a real phone; a gradual indicator change; a paid planner canary (W8).

**Two things I did not diagnose.** One browser-smoke run raised `StopIteration` straight after the Environments build; two reruns passed 27 of 27. Seeding the library over the previous store raised `ConflictingRecord` (the same HTML with different metadata is never replaced), so I set that local store aside, rebuilt it (16 of 16 `kit-verified`) and removed the old file.


## Stage 3: the fermentation bench (2026-10-25)

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | The energy model: spec, registration suite (10 planted bugs), independent reference, manifest, pointers | `science/respiration_energy.ts`, `science.test.ts`, `api/verify/references.py`, `data/citations/pointers.json` | Kit tests; `test_plan_fermentation.py` | Done |
| 2 | `dial` and `fermentationScene` | `dial.ts`, `fermentation_scene.ts`, `style.ts`, `manifest.ts`, `index.ts` | `dial.test.ts` | Done |
| 3 | Plan fields (`surface: dial`, scene kind `fermentation` with `model`), PLAN-018 and PLAN-019, assembler, the 17th golden Plan | `plan.py`, `plan_checks.py`, `assemble.py`, `data/plans/biology-f4-fermentation.json` | `test_plan_fermentation.py` | Done |
| 4 | The verifier and the harness: `dial_dead` (L2-009), `_drive_dials`, `_fermentation_problems`, bindings | `api/verify/{provenance,render}.py`, `failchecks.py` | `test_dial.py` | Done |
| 5 | Review answers: pathway pinned; page-made drawings and added text refused; `binding_problems`; real keys read from the audit; verifier-only split (`foreign`, `exact`); the textbook's variables | `fermentation_scene.ts`, `parts.ts`, `audit.ts`, `provenance.ts`, `plan.py`, `plan_checks.py` | `test_dial.py`, L6 | Done |
| 6 | L4 case set regenerated (a declared amendment), planner pack v5 | `data/l4/cases.json`, `cases.sha256`, `eval/l4/test_l4.py`, `planner.v5.md` | `eval/l4` | Done |
| 7 | Planted defects | `eval/l6/mutations.py`, `data/fixtures/envs/reference-fermentation.*` | L6 | Done |
| 8 | Relock the Kit | `packages/kit/kit-lock.json` | build hash `fb33e0e7babf` | Done |

**Verification (run 2026-10-25):** `pnpm --filter @synapse/kit test` (417); `pnpm -r typecheck`; ruff; pyright; `uv run pytest -q` (987 passed, 1 skipped (983 in the full run; the 4 failures were a stale surface test, two over-long pointer claims, and two generated reports, and their files were rerun)); `eval/l6/run.py` (151 of 156 planted defects refused, 0 of 16 false positives, no surprise misses); `eval/hostile/run.py`; `eval/environments/build.py --corpus ...` (17 of 17 `kit-verified`); `eval/smoke/web_smoke.py --no-build`; `eval/cost/project.py`; a screenshot of the bench after turning the dial.

**Notes.** A screenshot of my own first build showed the Kit blanking the page: Playwright injects a stylesheet and the new no-CSS rule was in the runtime self-check. That is D-46's correction; it would have hit any student with a dark-mode or translation extension. My own test mistakes fixed: a step value that was on the grid (0.0035), a snap I computed wrongly, a rule name in an assertion. **Not done:** stage 4; the V3 setup drags and timer (recorded in D-46); a screen-reader pass; a real phone; a paid planner canary (W8).
