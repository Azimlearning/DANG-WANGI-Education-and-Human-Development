# Execution: the completion roadmap

> Plan: `refdocs/plans/2026-10-22-completion-roadmap.md`. How and in what order. Keep this file true to what happened (CLAUDE.md rule 4). Only W0 is detailed here; W1 to W11 each get their own plan and execution pair (use `/plan-feature`) before any code, and are listed below with their first step and their Verify.

## Before starting any workstream

- `git status` clean on `main`; read `refdocs/STATUS.md` and `.claude/memory/preflight.md`.
- The baseline is green: `uv run pytest -q`, `pnpm -r test`, `pnpm codegen:check`, `uv run python eval/l6/run.py` (56 of 61 refused, 0 of 12 false positives), `uv run python eval/hostile/run.py` (20 of 20). Record the counts at the start of each workstream; do not copy them from older rows.
- Library and framework docs are read before writing against them (rule 6). A Kit change relocks (D-29) and goes through `kit-guardian`. A wire change starts in `packages/schema`. A prompt change is a `prompt:` commit with an eval delta. A paid run follows rule 7 and D-40.

## W0: ground truth and decisions

| # | Task | Files | Status |
|---|---|---|---|
| 1 | Commit the pending 2026-10-21 research docs on their own | `refdocs/changelog/*`, `refdocs/evidence/*` | Done 2026-10-22 (commit e72d0fb, local, not pushed) |
| 2 | Fix the STATUS drift: P5 to 🔶 with the reason, a roadmap pointer, a ledger row for the Kit lock and test counts | `refdocs/STATUS.md` | Done |
| 3 | ADRs D-38, D-39, D-40, and the PRD decision log rows D-34 to D-40 (D-34 to D-37 were missing), plus the Present mode note under the PRD non-goals | `refdocs/changelog/DECISIONS.md`, `refdocs/synapse-v4-PRD.md` | Done |
| 4 | The umbrella plan and this execution doc | `refdocs/plans/2026-10-22-completion-roadmap.md`, this file | Done |
| 5 | Index rows for the missing plan and these two docs | `refdocs/plans/README.md`, `refdocs/execution/README.md` | Done |
| 6 | Rewrite `remaining_work.md` without the deadline framing and with the new workstream map | `refdocs/guides/remaining_work.md` | Done |
| 7 | Changelog entry | `refdocs/changelog/CHANGELOG.md` | Done |
| 8 | Save the owner's standing preferences to memory (time is not a variable; completion scope) | Claude memory directory (outside the repo) | Done |

**Verify (W0):** `git status` shows only the intended docs; the Kit lock quoted in STATUS equals `packages/kit/kit-lock.json` (`bf41463c9944`); `grep -rn` for an em dash or en dash over the new and edited docs finds none; every ADR id in `DECISIONS.md` has a row in the PRD decision log.

## W1 to W11: first step and Verify

| W | First step (before any code) | Verify |
|---|---|---|
| W1 | `/plan-feature` for L4 and Free. Read `api/verify/mint.py`, `api/pipeline/failchecks.py`, `eval/l6/mutations.py` and `api/prompts/verifier_l4.v1.md`. Decide the L4 verdict wire shape | L6: `page-false-prose` refused, 0 of 12 false positives; hostile 20 of 20; a Free fixture mints only `model-checked`; `kit-guardian` clean |
| W2 | `/plan-feature` for the library path. Read `api/pipeline/run.py` 225 to 320 and `api/verify/store.py` (`lookup_question`, `latest_id`) | A spy-provider test sees zero provider calls on a covered topic; the environment event arrives in under one second locally |
| W3 | `/plan-feature` for the UI port. Pin the V3 repo commit being ported; read the current Next 16, React 19 and Tailwind 4 docs; read `Synapse-V3/design/BRAND.md` and `FLOW.md` | `pnpm -r test`; `eval/smoke/web_smoke.py` all green plus new checks (toggle reaches the frame, 44 px targets, no scroll at 360 px); screenshots against V3 |
| W4 | `/plan-feature` for the interaction Kit. Build Hooke's drag bench first, then the rest | Kit registration suites refuse every planted defect; the new Environments are `kit-verified`; L6 has no regression |
| W5 | One plan each for C1, C2, C3. C3 needs a design doc first | Chromium run of three misconceptions end to end; a recorded-row report matches the table; marking-scheme tests cover right, partial and wrong answers |
| W6 | One plan each for C4, C5, Present mode, B4. Confirm Present mode's behaviour with the owner (D-39 `ASSUMED`) | `pnpm codegen:check`; an unreviewed BM string never renders; a chapter pack opens offline with every hash checked |
| W7 | One plan per item; B8 batches by measured gap | `eval/evidence/leak_check.py` clean; every new Environment `kit-verified`; census coverage reported |
| W8 | cost-auditor, projection, hard bound, then the owner's typed amount | Results JSON in `eval/golden/results/` and an evidence note with pass rate, cost and latency |
| W9 | Follow `refdocs/guides/guardian_pass.md`; the owner watches | `refdocs/evidence/<date>-p1-guardian-round4.md`; smoke a11y checks green; CI green on a pushed branch |
| W10 | Walk `refdocs/guides/checklist.md` "Before any public deploy" | Each item ticked and recorded in the changelog |
| W11 | Prepare review packs for the owner to hand to a teacher and a BM reviewer | Labels above `kit-verified` appear only with a recorded reviewer |

## Wrap-up for every workstream

`/session-end`: changelog entry with an honest **Verified** line, the STATUS phase table and ledger, any ADR, the plan and execution index rows, and `env_setup.md` if a setting changed.
