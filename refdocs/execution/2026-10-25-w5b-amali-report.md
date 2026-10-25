# Execution: W5b, the Amali lab report

> Plan: `refdocs/plans/2026-10-25-w5b-amali-report.md`. Keep this file true to what happened (CLAUDE.md rule 4). No paid call is made by anything here.

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | `synapse_lab` in the bridge; table, experiment and stepper post it; not in the public surface | `packages/kit/src/{bridge,table,experiment,stepper}.ts`, tests | Kit tests | Done |
| 2 | Relock the Kit | `packages/kit/kit-lock.json` | build hash recorded | Done |
| 3 | Host parser and report state | `web/lib/{sandbox,labreport}.ts`, tests | web tests | Done |
| 4 | The panel, text export, Stage integration | `web/components/LabReport.tsx`, `EnvironmentFrame.tsx`, `Stage.tsx` | web tests | Done |
| 5 | Smoke at 360 px | `eval/smoke/web_smoke.py` | smoke | Done |
| 6 | L6, hostile, Environments, kit-guardian review | | runs | Done |
