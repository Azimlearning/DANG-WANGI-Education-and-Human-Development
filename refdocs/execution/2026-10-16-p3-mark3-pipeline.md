# Execution: P3 The Mark 3 pipeline

> Plan: `refdocs/plans/2026-10-16-p3-mark3-pipeline.md`. A task is not done until its Verify passes. If reality diverges, edit this doc.

## Before starting

- P1 is done (L1 to L3, three science models, Kit 0.1.x). Read D-21, D-23 and the research note.
- No paid call. `SYNAPSE_LLM_MODE=fake`. The fake planner and filler are deterministic functions of the prompt, plus scripted ones for tests.
- Rule 6: read the current docs for any library used. Pydantic's JSON Schema generation is the one new API.

## Task 1: The Plan model and the plan checks

**Files:** `api/pipeline/plan.py`, `api/pipeline/plan_checks.py`, `api/prompts/schemas/plan.schema.json` (generated), tests.

**Steps:** a strict Pydantic `Plan` (id, goal, pattern, experiment ref, controls with id, label, unit, min, max, grid and default, models with id and parameters, readouts with label, unit, digits and source, tasks, steps, study note, citation ids, presentation hint, `custom` parts with names and contracts). The plan checks (codes PLAN-001 and up): schema; model id in the manifest; parameters and control ranges inside the model's domain; every readout bound to a model or a declared constant; no unbacked number in copy (the same rule as L1); every named component exists in the manifest; size and budget. Domain data comes from the built manifest, not from the Kit source.

**Verify:** `uv run pytest api/pipeline -q`: a valid hand-written Plan for each of the three models passes; each bad Plan (unknown model, k = 0, range below a domain minimum, a readout with no source, an unbacked number, a missing component, an oversize study note) is refused with its code and a hint; the JSON Schema file matches the model (drift test).

## Task 2: The fail-check registry

**Files:** `api/pipeline/failchecks.py`, `api/pipeline/test_failchecks.py`.

**Steps:** a `FailCheck` record (code, layer, rule, severity, repair, model_hint, student_message). Register every rule the verifier, post-processor, plan checks, slot checks and gate can emit. A test collects the rule strings from the source (the `Problem(...)`, `VerificationFailed(...)`, `PostprocessReject(...)` and `ScanReject(...)` calls and the `refusal()` returns) and fails if one is unregistered or a registered rule is unreachable.

**Verify:** the coverage test passes and fails when a rule is added to the verifier without a registry entry (proved by a temporary edit).

## Task 3: The prompt packs and the assembler

**Files:** `api/prompts/**` (the packs), `api/pipeline/prompts.py`, tests.

**Steps:** write the packs listed in the plan, each with front matter and an eval-delta note. A loader validates the front matter (required keys, a known tier, variables used equal variables declared, a schema reference that exists, a token budget). The assembler builds a request from segments in cache order, substitutes variables only in non-stable segments, builds the kit pack from the manifest by `useWhen` retrieval, and estimates tokens against each budget. Pattern packs' failure-mode sections are generated from the registry.

**Verify:** every pack loads; the stable prefix is byte-identical across two requests that differ only in variables; a pack over its budget fails; a variable declared but unused (or the reverse) fails; the kit pack for each hand-written Plan contains exactly the components the Plan names and no more than 15.

## Task 4: Skeletons and the assembler

**Files:** `api/pipeline/skeletons/{simulation,virtual_experiment}.html`, `api/pipeline/assemble.py`, tests.

**Steps:** two skeletons with named slots. The assembler fills slots from a Plan (controls, models, readouts, study note, tasks, steps), refuses a Plan the skeleton cannot take (a `gap`), and emits a complete document that starts with the Kit script.

**Verify:** for the three Physics Form 5 Plans the assembled HTML is minted by the real verifier (`verify_environment`) with the Plan's models as `plan_models`; no model call is made; the checked record lists the six layers.

## Task 5: Slot fills with contracts

**Files:** `api/pipeline/fill.py`, tests.

**Steps:** a slot has a name, a signature, the Kit calls it may use, a maximum length. A fill is accepted only if it parses, stays within the allowed calls and length, and contains none of the L0 forbidden patterns. A fake filler produces fills for tests.

**Verify:** a fill that calls a forbidden function, exceeds its length, or references an undeclared identifier is refused at the slot with FILL-* codes; a valid fill is inserted and the page is minted.

## Task 6: The pipeline orchestrator

**Files:** `api/pipeline/run.py`, `api/pipeline/events.py`, tests.

**Steps:** run the layers in order on fakes, emitting events (stage, plan, text, environment, error, done). Implement repair, the single targeted retry, the budget per request, and the degrade ladder. Every layer writes a trace record.

**Verify:** injected failures at each layer land on the right rung of the ladder; a budget overrun degrades instead of starting a revision; traces exist for every layer; the stream order is stable.

## Task 7: Generation micro-components the first two skeletons need

**Files:** `packages/kit/src/{reset,graph,table,experiment,stepper}.ts`, manifest entries with `useWhen`, tests, a Kit version bump.

**Steps:** build `reset`, `graph`, `resultsTable`/`record`, `experiment` and `stepper` to the PRD 3.4 rules; add `useWhen` and argument descriptions to every manifest entry; bump the Kit and relock (D-16).

**Verify:** Kit tests (accessibility names, 360 px, planted-defect refusals); the assembled Environments using them are minted.

## Task 8: The loading skeleton in the web shell

**Files:** `api/pipeline/events.py`, `packages/schema/src/events.ts` (a `PlanEvent`), `web/components/PeekSkeleton.tsx`, tests, the smoke.

**Steps:** stream a small `plan` event once the plan checks pass; the web draws the Peek shell from it and replaces it with the verified Environment.

**Verify:** unit tests for the skeleton; the real-browser smoke sees the shell before the Environment.

## Task 9: Golden and hostile sets, and the cost projection

**Files:** `eval/golden/vertical.yaml`, `eval/hostile/`, `refdocs/evidence/<date>-p3-cost-projection.md`.

**Steps:** a golden set of Physics Form 5 questions mapped to topics and Plans; hostile inputs for the intake layer; a projection of cost per Environment as a range with every assumption named, using the pricing table marked ASSUMED. **Do not make a paid call. State the projected amount and wait for the owner (rule 7).**

**Verify:** the golden set pins its hash; the projection is written and lists what the first smoke run would be.

## Task 10: Wrap-up

STATUS, CHANGELOG, DECISIONS, indexes, the Deferred to local register, `kit-guardian` review of the Kit and pipeline diff.
