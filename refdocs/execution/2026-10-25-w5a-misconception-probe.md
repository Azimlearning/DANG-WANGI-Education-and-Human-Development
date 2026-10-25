# Execution: W5a, the misconception probe

> Plan: `refdocs/plans/2026-10-25-w5a-misconception-probe.md`. Keep this file true to what happened (CLAUDE.md rule 4). No paid call is made by anything here.

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | Pick the threshold from the sweep | `eval/models/misconception_eval.py` (read only) | recorded in the ADR | Done |
| 2 | `data/probes.json` and its loader | `data/probes.json`, `api/models/probes.py`, `api/models/test_probes.py` | planted-fault tests | Done |
| 3 | The `probe` event in the schema, codegen | `packages/schema/src/events.ts`, `api/schema/generated.py` | `pnpm codegen:check` | Done |
| 4 | Emit it before `done` | `api/pipeline/run.py`, `api/pipeline/test_probe.py` | tests incl. spy provider | Done |
| 5 | Parse it and render the card | `web/lib/{stream,turns}.ts`, `web/components/ProbeCard.tsx`, `MessageList.tsx` | web unit tests | Done |
| 6 | Smoke at 360 px | `eval/smoke/web_smoke.py` | smoke | Done |

## Verification (2026-10-25, cloud container, shimmed Chromium)

`uv run pytest api/models/test_probes.py api/pipeline/test_probe.py api/routes` (18 + 4 + routes, all passed); `pnpm codegen:check` OK after `pnpm codegen`; `pnpm --filter web test` (85 passed); `pnpm --filter web exec tsc --noEmit` clean; `uv run ruff check api eval` and `uv run pyright api eval` clean; `eval/smoke/web_smoke.py --no-build` 32 of 32 (5 new probe checks at 360 px: the card appears, every control is at least 44 px, no answer before choosing, a right answer is said in words with its basis, no horizontal scroll).

## Notes

- The threshold task ran as a restricted sweep through `probe_for` over the 50-question probe set, not by editing the eval script; the figures are in `refdocs/evidence/2026-10-25-w5a-probe-threshold.md`.
- Not done: the other two entries' probes, a screen-reader pass of the card, a real phone, a teacher's reading of the three corrections.
