# Execution: P1 Kit core and verification

> Plan: `refdocs/plans/2026-10-16-p1-kit-core-and-verification.md`. Tasks run top to bottom. A task is not done until its Verify step passes.
> If reality diverges, edit this doc (CLAUDE.md rule 4).

## Before starting

- P0 is built and verified (STATUS). Read the changelog entry for the kit-guardian findings, D-16, D-17 and D-21.
- This phase bumps the Kit to 0.1.0 (D-16): provenance changes behaviour. Stored Environments from P0 go stale and are reseeded.
- No paid call is made in P1. Fakes only.

## Task 1: Label ladder and the `checked` summary on the wire

**Files:** `packages/schema/src/blocks.ts`, `api/schema/generated.py` (generated), `api/verify/mint.py`, `api/verify/store.py`, `api/verify/gate.py`, `web/lib/stream.ts`, `web/components/Provenance.tsx`, the fixtures' plan JSON, the tests that name `dev-fixture`.

**Steps:**
1. Remove `dev-fixture` from `TrustLabel`. Add `CheckedSummary` (layers, controlsExercised, gridPoints, referenceCases, readouts, models as `{id, params}` pairs) and a `checked` field on `EnvironmentBlock`. Run `pnpm codegen`.
2. The mint allows `model-checked` only until P2; `guard_label` keeps its rules. The store and gate carry `checked` through; the gate refuses a row without it.
3. The web guard parses `checked`; the Provenance component gets a "What was checked" list from it, in words, with the limits.

**Verify:** `pnpm codegen:check` clean after a deliberate drift test; a test proves `dev-fixture` cannot be minted or parsed; the web unit tests show the panel text.

## Task 2: Provenance in the Kit (0.1.0)

**Files:** `packages/kit/src/{provenance,observable,environment,slider,readout,text,constant,index,manifest}.ts`, `packages/kit/build.mjs`, tests.

**Steps:**
1. A module-private `WeakSet` of real observables and a `WeakMap` of provenance nodes (`control`, `model` with id and params, `constant`, `derived`, `free`). `isObservable` checks the set, not the shape. `observable()` created by generated code is kind `free`.
2. `Synapse.constant(value, {label, unit})` for a declared fixed value (an input to a model; a readout of a bare constant is refused); `Synapse.text(env, string)` for sanctioned copy. Ownership is a private map of element to expected text (not a DOM attribute, which a script could copy); see D-24.
3. Every Kit component marks the elements it creates as owned. `readout` records its observable's provenance and a formatter, so the audit can recompute its text.
4. `window.Synapse` is defined once with `Object.defineProperty` as non-writable, non-configurable, and frozen. A second definition throws.
5. `Synapse.audit()` returns a plain, serialisable record: controls (id, min, max, grid, value), readouts (label, unit, digits, displayed text, observable value, formatted value, provenance chain), copy numbers, and constants.
6. Bump to 0.1.0 and relock the new version.

**Verify:** `pnpm --filter @synapse/kit test` includes: a hand-built object with the observable shape is refused by `readout`; `window.Synapse = x` throws in strict mode; a second Kit load throws; the audit of the good fixture lists one control and one readout grounded through `mechanics.hookes`.

## Task 3: Science registration framework and two more models

**Files:** `packages/kit/src/science/{spec,model,hookes,ohm,pressure_depth}.ts`, `packages/kit/src/science/science.test.ts`, manifest entries.

**Steps:**
1. A `ScienceSpec` type: id, units for inputs and output, domain, citation (`UNVERIFIED`), reference cases with a derivation string, properties, planted bugs. One generic `registrationFailures(spec, impl)`.
2. Move `hookes` into the framework. Add `electricity.ohm` (current = voltage / resistance; power was not built) and `fluids.pressure_depth` (pressure = depth x density x g). Each has at least 8 planted bugs.
3. Manifest entries carry units, domain and the citation status.

**Verify:** the suite accepts each real model and refuses every planted bug; the report prints `n/n` detected per model.

## Task 4: Independent Python references

**Files:** `api/verify/references.py`; its tests are in `api/verify/test_provenance.py` (there is no `test_references.py`).

**Steps:** hand-write each model's reference from the formula, in Python, without reading the TypeScript, and compute a table of worked values by hand (the arithmetic is written out in comments). Where the model has a second route to the same answer, use it as a property (for example Hooke's law: the elastic energy `E = F^2 / (2k)` must equal `F * x / 2`; Ohm's law: `V^2 / R` must equal `V * I`). A registry maps a model id to its reference function and parameter schema. Both implementations share the author, so a shared misunderstanding is possible; the textbook worked examples in P2 are the real independent check.

**Verify:** `uv run pytest api/verify/test_provenance.py -q`: the worked values, properties and domain refusals pass. **Deviation:** the energy second-route properties (`E = F^2 / 2k`, `V^2 / R = V I`) were not written; the references carry hand-computed worked values and the Kit-side properties only.

## Task 5: L1 provenance, L2 grid and extremes, L3 cross-check in the harness

**Files:** `api/verify/render.py`, `api/verify/mint.py`, tests, new planted fixtures.

**Steps:**
1. After ready, call `Synapse.audit()`. L1 refuses: a readout whose provenance is not grounded in a control through a science model (a bare declared constant is refused, a model fed in the wrong unit is refused); a readout whose displayed text differs from its formatted value; any numeric text outside owned elements; a `window.Synapse` that is not the frozen Kit.
2. L2 sweeps the declared grid of each control with the others at default, plus every combination of min, mid and max up to a cap, and checks every readout is finite and nothing threw.
3. L3 reads the audit at each point, evaluates the Python reference for each model with the recorded parameters and control values, and refuses a mismatch beyond the display rounding. It also compares the recorded model parameters to the plan JSON's `models`.
4. Fill the `checked` summary from what was actually run.

**Verify:** the good fixture is minted; `bad-bypass` (hand-typed text) is refused as `readout_mismatch`; a constant wrapped in an observable is refused as `ungrounded_readout`; a changed parameter is refused as `plan_mismatch`; a typed number in a paragraph is refused as `unowned_number`; a forged observable is refused. Earlier planted fixtures still refuse at their layers. The `test_bad_bypass_is_NOT_caught` test is flipped.

## Task 6: Core components and fixtures for the three models

**Files:** `packages/kit/src/{reset,graph,table}.ts`, `data/fixtures/envs/{reference-ohm,reference-pressure}*.html` and plans, tests.

**Steps:** `reset` restores every control to its default and the readouts follow. `graph` draws an SVG line with axes and a visually hidden table as its text equivalent. `table` shows recorded results. Write a good fixture for each new model and one planted variant for each.

**Verify:** Kit tests and a 360 px render check pass for all three fixtures; each is minted.

## Task 7: L6 baseline

**Files:** `eval/l6/{mutations,run}.py`, `refdocs/evidence/2026-10-16-p1-l6-baseline.md` (generated), tests.

**Steps:** mutation operators over the good fixtures: change a model parameter, replace a readout's source with a constant, overwrite readout text, add a typed number, forge an observable, redefine the global, add an undeclared control, a dead control, a self-moving readout, a hidden `eval`, a navigation, a `fetch`, a hidden `fetch`. Run each through the real verifier. Report which layer refused each, the detection rate per layer and overall, and the classes not tried.

**Verify:** `uv run python eval/l6/run.py` prints the table; the generated report states that the planted classes are those thought of, not the space of bugs.

## Task 8: Hostile set

**Files:** `data/hostile/*`, `eval/hostile/run.py`, tests.

**Steps:** read v3 `evals/hostile.yaml` in full; port each case as an HTML document or generation prompt with provenance; run the HTML ones through the verifier and record the layer that blocked each.

**Verify:** every ported HTML case is blocked at two layers where two apply, and the run prints the block rate.

## Task 9: Isolation spike (A-10)

**Files:** `refdocs/evidence/2026-10-16-p1-isolation-spike.md`, a small script under `eval/isolation/`.

**Steps:** in the container, try the harness under `unshare` network and user namespaces and resource limits; record what works, what fails, and the cost. Do not claim a public-deploy decision: write the options and what each needs.

**Verify:** the note records commands and results; A-10 in the PRD and DECISIONS is updated with what was observed.

## Task 10: Review and wrap-up

- Run the `kit-guardian` agent over the P1 diff; fix or record every finding.
- STATUS (phase table, ledger, known gaps, deferred to local), CHANGELOG, DECISIONS, this doc, the plans and execution indexes.

## As built (reconciled 2026-10-16)

- Tasks 1 to 9 are done; task 10's review ran twice. Round 1 found 18 bypasses (all fixed, see D-24 and the changelog). Round 2 was stopped by a safety classifier and tested nothing, so a fresh review is open.
- Beyond the plan: `dom.ts`, `lockdown.ts`, `watch.ts` (runtime self-check), forbidden-markup audit, `series` and `actions` in the audit, a `wrong_unit` / `wrong_input_unit` / `constant_readout` / `control_mismatch` / `forbidden_markup` / `malformed_audit` / `plan_missing` rule set, `eval/l6` (61 mutations), `eval/hostile`, `eval/isolation`, and `__SYNAPSE_VERIFY__`.
- The L6 report is a regression baseline: the mutation set grew as holes were found.
- Not done from the plan: energy second-route properties in the references; `ohm` power output.
