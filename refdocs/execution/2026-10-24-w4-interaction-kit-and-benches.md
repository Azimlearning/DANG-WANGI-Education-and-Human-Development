# Execution: W4 stage 1, the Hooke mass bench

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
