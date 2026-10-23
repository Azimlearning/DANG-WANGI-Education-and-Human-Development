# Execution: W1, the L4 wording check and the Free lane

> Plan: `refdocs/plans/2026-10-22-w1-l4-and-free-lane.md`. How and in what order. Keep this file true to what happened (CLAUDE.md rule 4). No paid call is made by anything in this file.

## Before starting

- `git status` clean on `main`. Baseline recorded in task 1 before any edit.
- Read: `api/verify/mint.py`, `api/verify/render.py` (HARNESS and `_exercise`), `api/verify/gate.py`, `api/pipeline/run.py`, `api/pipeline/failchecks.py`, `api/pipeline/test_failchecks.py`, `api/prompts/__init__.py`, `eval/l6/mutations.py` (done when this doc was written).
- Commands use `uv run`; Chromium-backed tests are slow (the full suite took about 8 minutes on 2026-10-18).

## Tasks

| # | Task | Files | Verify |
|---|---|---|---|
| 1 | Record the baseline | none | `uv run pytest api/pipeline api/verify api/prompts -q` and `pnpm --filter web test`; write the counts into the changelog entry |
| 2 | Register the new rules `L4-001` (wording refused, `retry_plan`) and `FREE-001` (reply is not one HTML document, `text_only`) | `api/pipeline/failchecks.py` | `uv run pytest api/pipeline/test_failchecks.py -q` passes once the code emits both (the test fails if a registered rule is never emitted) |
| 3 | The wording module: `plan_texts`, `page_texts`, `parse_verdict` (strict, fails closed), `WordingVerdict` | `api/pipeline/wording.py`, `api/pipeline/test_wording.py` | Tests: every prose field of every golden Plan appears; scripts and styles are excluded from a page's visible text; malformed, non-JSON, missing-key and extra-key replies are not a pass |
| 4 | Prompt packs and builders: `verifier_l4_free.v1.md`, `free.v1.md`; `prompts.wording_request`, `prompts.free_wording_request`, `prompts.free_request`; the pointer `claim` (never the quotation) as the passage | `api/prompts/*.md`, `api/pipeline/prompts.py`, `api/pipeline/test_prompts.py` | The pack loader accepts both (placeholders match inputs, budget holds); a test asserts no corpus quotation can reach a request; the existing prompt tests pass |
| 5 | Fakes: `wording_responder` (ok unless a text carries the marker `[[FALSE]]`), `free_responder` (a compliant page) | `api/pipeline/fakes.py`, `data/fixtures/envs/free-sample.html` | The fake plan, wording and free paths run offline; no socket opened (the repo-wide guard in `conftest.py`) |
| 6 | Harness: for `kit_lane=False` the page is ready when the iframe loads (two animation frames). Free fixtures: a good page and four bad variants (fetch, navigates itself, unnamed control, control that changes no readout) | `api/verify/render.py`, `data/fixtures/envs/free-*.html`, `api/verify/test_verify.py` | Real Chromium: the good page mints as lane `free`, label `model-checked`; each bad variant is refused at `forbidden_api`, `navigation`, `a11y`, `dead_control`; the Kit-lane tests still pass |
| 7 | Mint and gate: `verify_environment(..., wording_checked=False)` adds the layer `wording`; the gate's `limits` is lane-aware (a Free line) | `api/verify/mint.py`, `api/verify/gate.py`, tests | A test shows `wording` only when asked and never for a call that did not ask; a Free row's limits text says it was written whole by a model; `kit-verified` with `lane="free"` is still refused |
| 8 | Pipeline: wording inside the plan loop (issues go back to the planner once); Free fallback on `AssemblyGap` and on plan failure when enabled and the topic is not `none`; the gap log; `MAX_LLM_CALLS` 6 to 8; `Deps.wording_check`, `Deps.free_lane`, `Deps.gap_log_path` | `api/pipeline/run.py`, `api/pipeline/gaplog.py`, `api/pipeline/test_run.py` (or the file the existing pipeline tests use) | Tests with fake providers: a flagged Plan is retried once then degrades; a passing judge adds `wording` to the stored layers; Free off (default) behaves as before; Free on with an assembly gap delivers a Free Environment and appends a gap record that holds no question text; Free refuses when the judge says no or is unavailable; budget exceeded degrades |
| 9 | Settings and wiring: `FREE_LANE_ENABLED` (default false); `wording_check` on only in live mode; `env_setup.md`; `.env.example` is blocked to the tools, so the line is given to the owner | `api/core/settings.py`, `api/app.py`, `refdocs/guides/env_setup.md` | `uv run pytest api/core api/routes -q`; the app builds `Deps` with the flags from settings |
| 10 | Web: plain-words text for the `wording` layer in the Provenance card | `web/components/Provenance.tsx` and its test | `pnpm --filter web test` |
| 11 | The L4 measurement protocol, fixed before any paid run: planted false and true wording cases drawn from the 16 Plans, a scorer, and an offline stub run | `eval/l4/cases.py`, `eval/l4/run.py`, `eval/l4/test_l4.py`, `data/l4/cases.json` | `uv run python eval/l4/run.py` prints cases and the stub's score and states that a stub measures plumbing only; the case file's hash is pinned in the test |
| 12 | Review: regenerate the cost projection; run `cost-auditor` and `kit-guardian` over the diff; answer every finding | `eval/cost/project.py` output, review notes | Both agents' findings listed in the changelog with the action taken |
| 13 | Whole-repo verification | none | `uv run pytest -q`; `pnpm -r test`; `uv run ruff check api eval`; `uv run pyright api eval`; `pnpm -r typecheck`; `pnpm codegen:check`; `uv run python eval/l6/run.py` (56 of 61, 0 of 12 false positives); `uv run python eval/hostile/run.py` (20 of 20); `uv run python eval/environments/build.py --corpus C:/Users/User/synapse-corpus/text` (16 of 16 `kit-verified`, report unchanged); `uv run python eval/smoke/web_smoke.py` |
| 14 | Wrap-up | `STATUS.md`, `CHANGELOG.md`, `DECISIONS.md` (D-41), PRD decision log, plan and execution index, `remaining_work.md` | `/session-end` checklist |

## Deviations from the roadmap (W1 entry)

The roadmap said the L6 run would flip `page-false-prose` (57 or more of 61). That is dropped on purpose: a stub judge in L6 would raise the verifier's reported detection rate without any real model being measured. `page-false-prose` stays a known miss of the model-free layers (the pin in `eval/l6/test_l6.py` stays); L4's real detection rate is measured in W8 against the fixed case set from task 11.

## Notes kept while building

- **Done 2026-10-23.** Tasks 2 to 14 are built and verified (see the STATUS ledger row of 2026-10-23). The two reviews added work that is not in the task table: the Free-lane scan, `LLMService.would_fit`, fenced judge packs (`verifier_l4.v2`), unreadable-page refusal, comment stripping, no verify flag and no action exemption for Free pages, no wording claim for a page with a fill, and L4 refusals not falling to Free. All are in D-41's amendment.
- **Deviation from task 4:** `free_wording_request` takes the routed topic, not the question (injection channel); `verifier_l4.v2` was added beside v1 instead of using v1.
- **Deviation from task 8:** `MAX_LLM_CALLS` 8 was kept, and the Free path checks that two calls and the caps remain before the page is paid for.
- **Deviation from task 9:** `eval/golden/live.py` does not set `wording_check` or `free_lane`, so a golden live run measures neither; W8 adds the flags. `.env.example` is still blocked to the tools: add `FREE_LANE_ENABLED=false`.
- **Batching:** tests and documents were run and written in blocks at the owner's request (2026-10-22 and 2026-10-23).
