# Plan: P1 Kit core and verification

> Phase P1 of `refdocs/synapse-v4-PRD.md` section 6. Execution doc: `refdocs/execution/2026-10-16-p1-kit-core-and-verification.md`. Resolves the open items P0 left in `STATUS.md` (a hand-typed wrong number is not caught, the verifier's detection rate is unmeasured, isolation is undecided).

## Why this exists

P0 proved one Environment can travel the whole trust path, and the kit-guardian review showed where that path is thin. The render harness can tell that a control changes a readout; it cannot tell that the number is right or that it came from science. A generated page can wrap a typed constant in an observable, overwrite a readout's text, or show a number in a plain paragraph, and every P0 layer passes it. P1 makes the verifier able to say what a number is and where it came from, and measures how often it is right.

It also removes the P0-only label (D-21), adds the next two science micro-models for the first vertical (D-18), and answers the isolation question (A-10) before any generated code is served to anyone.

## What's already covered (no work needed)

| Need | Where |
|---|---|
| Sandbox, CSP first, hash check, mint, gate, kit lock | P0 (D-06, D-16, D-17) |
| One science micro-model with a registration suite and planted-bug detection | `mechanics.hookes`, `packages/kit/src/science_registration.ts` |
| Render harness with real input, navigation and accessibility checks | `api/verify/render.py` |
| Hostile cases | Synapse v3 `evals/hostile.yaml` (to port, with provenance) |

## Scope

**In:**
1. The label ladder (D-21): remove `dev-fixture`; add the `checked` summary to the wire block so the student can see what was checked (enhancement N10).
2. Provenance in the Kit: unforgeable observables, a provenance graph, a frozen non-replaceable `window.Synapse`, owned DOM, a `constant` and a `text` component so sanctioned copy and fixed values are declared, and an audit view the harness reads.
3. A general science micro-model registration framework, and two more models: `electricity.ohm` and `fluids.pressure_depth`, each with units and domain, a hand-written reference, properties and planted physics bugs.
4. Independent Python references for every model (`api/verify/references`), hand-written, not generated from the TypeScript.
5. L1 provenance, L2 grid and extremes, L3 numeric cross-check in the harness, and the new refusal rules.
6. The L6 baseline: planted variants of real Environments, the detection rate per layer, reported not assumed.
7. The hostile set port and a block-rate check.
8. The isolation spike: what can the verification worker run under in a container without network.
9. Core UI and scene components: `reset`, `graph` (with a text-equivalent table), `table`.

**Out (and why):**
- Real textbook citations and `kit-verified`: needs the corpus (P2, local). Cloud-built Environments top out at `model-checked` (D-21).
- Scene components for specific apparatus (springs, circuits, tanks): P4, where the Environments are authored.
- A reachable goal state: belongs to a task, so P6 (challenge levels).
- The L4 LLM verifier: P3 (needs a live provider; D-08).
- Store attestation (A-19): P7 deploy gate.

## Approach

Provenance is the load-bearing idea. Instead of asking the harness to guess whether a number is real, the Kit records, for every observable, where it came from: a control, a science model with its parameters, a Kit-declared constant, or nothing. A readout is grounded only if its observable derives from a control through a science model. The harness reads this record through a frozen, non-replaceable object and cross-checks it three ways: the displayed text must equal the formatted value of the observable it claims; the value must equal an independent Python reference for that model at the same inputs; and no number may appear on the page outside Kit-owned elements.

Observables become unforgeable by being registered in a module-private WeakSet rather than recognised by shape, so a generated object that looks like an observable is refused. `window.Synapse` is defined once as non-writable and non-configurable.

The detection rate is measured by planting bugs, not assumed: each planted variant is a real Environment with one defect of a named class, run through the real verifier. The report says which layer refused each, and says plainly that the planted classes are the ones I thought of.

## Risks & unknowns

| Risk / unknown | Confidence | Mitigation |
|---|---|---|
| Generated code finds a way to forge provenance or replace the Kit | Medium that the first design is complete | Non-configurable global, private registry, kit-guardian review of the diff, planted variants for each forgery attempted |
| "No number outside owned elements" has false positives on legitimate copy | Medium | `Synapse.text` declares sanctioned copy and records any numbers in it for review |
| Python and TypeScript references share a mistake | Medium | The Python reference is written by hand from the formula and a different form of it, checked against the worked values; the risk is stated, and P2 adds textbook worked examples |
| The planted-bug detection rate flatters the verifier | High that it does | The report names the classes tried and says the rate applies to them only |
| Isolation tooling is unavailable in the container (no user namespaces) | Medium | The spike records what worked and what did not; the decision for a public deploy stays an owner decision |
| A Kit change forces a version bump (D-16) | Certain | P1 ships Kit 0.1.0; stored Environments go stale by design and are reseeded |

## Definition of done

- `dev-fixture` is gone from the schema, the web and the mint; a test proves it cannot be minted.
- `bad-bypass`, previously minted, is refused at a named layer; every earlier planted variant is still refused.
- Three science micro-models each have a citation field marked unverified, units and domain, an independent hand-written reference, properties and at least 8 planted physics bugs, all detected.
- The L6 report exists with a detection rate per layer and overall, and states its limits.
- The hostile set is ported and 100 percent blocked at two layers.
- The isolation spike is written up and A-10 is updated with what was observed.
- The web shows a "What was checked" panel from the stored `checked` record.
- Every line above is observed, with a ledger row in STATUS.
