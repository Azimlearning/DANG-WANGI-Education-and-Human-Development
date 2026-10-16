# Plan: P3 The Mark 3 pipeline (layered, skeleton-first)

> Phase P3 of `refdocs/synapse-v4-PRD.md` section 6, decision D-23. Execution doc: `refdocs/execution/2026-10-16-p3-mark3-pipeline.md`. Input: `refdocs/evidence/2026-10-16-chatgpt-ui-research.md` (how ChatGPT's apps UI works) and the owner's request to make the pipeline layered, with skeletons, deep prompt templates, fail checks and micro-components that make generation easier and cheaper.

## Why this exists

The PRD's pipeline is twelve stages in a table. It says what runs, not how the model's job is made small. The research shows the lever that matters: ChatGPT is reliable because the model supplies *data* and a developer-authored template renders it. Synapse has to let a model write a page, so it needs to rebuild that safety and cheapness inside the pipeline: shrink what the model writes toward data, generate the page by deterministic assembly wherever possible, and verify what remains.

Three expected benefits, each measured at P3 rather than assumed (A-4): fewer output tokens (cost), fewer verifier rejections (reliability), and a faster first useful paint (latency).

## What's already covered (no work needed)

| Need | Where |
|---|---|
| Fakes, the LLM seam, the cap and the ledger | `api/llm` (P0) |
| L0 to L3 and the mint, store and gate | `api/verify` (P0, P1) |
| The Kit manifest and the science micro-models | `packages/kit` (P0, P1) |
| The stream shape (meta, text, environment, done) and the web shell | `api/app.py`, `web/` (P0) |
| The router model | P1b |

## The layers

Every request passes the same ordered layers. A layer either passes its output on, repairs it deterministically, asks the model once more with named issues, or degrades the answer. No layer trusts the one before it.

| # | Layer | Does | Model | On failure |
|---|---|---|---|---|
| 0 | **Intake** | Canonicalise the question; bound length; screen the question text for prompt injection; text-only exit for non-science | none | Refuse politely |
| 1 | **Route** | Topic, domain, pattern, complexity, confidence | trained local model, LLM fallback below the gate (P1b) | Text answer only |
| 2 | **Look up** | Library hit by canonical key; experiment catalogue match; textbook passages (P2); misconception match | none | A library hit skips layers 3 to 8 |
| 3 | **Plan** | A validated Plan: goal, controls with ranges and grids, models with parameters, readouts, tasks, steps, study note, citation ids, presentation hint, and which parts are `custom` | LLM, forced tool use, schema-constrained | Retry once, then degrade |
| 4 | **Plan checks** | Deterministic checks on the Plan before any HTML exists: every model id is in the manifest, parameters and control ranges lie inside each model's domain, every readout is bound to a model, no unbacked number in copy, every needed component exists, size and budget | none | Repair (clamp, drop) or retry with the named issue, or mark the part `gap` and route it to the Free lane |
| 5 | **Skeleton** | Choose the pattern skeleton and build the kit pack: only the signatures of the components the Plan names | retrieval over manifest `useWhen` | n/a |
| 6 | **Assemble** | A deterministic assembler fills the skeleton from the Plan. If nothing is `custom`, the page is complete here with no generation | none | A skeleton that cannot take the Plan is a `gap` |
| 7 | **Fill** | For each `custom` slot only, the model writes a short typed fill (a function body with a contract, at most a set number of lines) | LLM, small | Slot-level retry, then drop the slot or go Free |
| 8 | **Verify** | L0 scan, L1 provenance, L2 grid and extremes, L3 reference, then L4 LLM check (pedagogy, units, scope and notation against the retrieved passage) | L4 only | Deterministic repair, then one targeted retry per named issue, at most 2 |
| 9 | **Mint, store, gate** | As P0 | none | Never serve on a failed gate |
| 10 | **Deliver** | Presentation chosen by the Composer; SSE events; client re-hash; sandbox | none | Honest degrade card |
| 11 | **Learn** | Trace every layer; log the gaps, Free generations and flags to the Kit backlog and to regression evals | none | n/a |

**Degrade ladder** (never a blank screen): Instantiate-by-plan, then Compose with fills, then Free (labelled, queued for review), then the text answer with a note. The text answer always streams first.

## Skeletons

Two kinds, both required.

1. **Generation skeletons.** One per pattern (simulation, virtual experiment, explorable diagram, process stepper, data visualisation, exam practice, Amali bench). A skeleton is a complete HTML document with named slots (`controls`, `models`, `readouts`, `scene`, `tasks`, `steps`, `custom:<name>`), written by us, verified by the full stack once per pattern, and instantiated from a Plan by the assembler. The model never writes the parts a skeleton already provides.
2. **Loading skeletons.** The Plan is streamed as soon as it passes the plan checks. The web shell draws the Peek card shell (title, study note, empty stage) immediately and swaps in the verified Environment, so the first useful paint does not wait for verification.

## Prompt packs (files, versioned; CLAUDE.md rule 7)

`api/prompts/<id>/v<n>.md`, each with front matter (id, version, purpose, tier, inputs, output schema, token budget, cache segment, owner), a stable body, and an eval-delta note. The assembler concatenates segments in cache order (stable first):

| Segment | Files | Stable? |
|---|---|---|
| core | `core/v1.md`: role, hard rules, Kit contract, bridge contract, accessibility, forbidden APIs, output format | yes, cached prefix |
| router fallback | `router_fallback/v1.md` | yes |
| planner | `planner/v1.md` and `schemas/plan.schema.json` (generated from the Plan model, drift-checked) | yes |
| pattern packs | `patterns/<pattern>/v1.md`: when to use it, required Plan fields, the skeleton's slots, an exemplar Plan, an exemplar fill, the failure modes to avoid (taken from the fail-check registry) | yes per pattern |
| kit pack | built per request from the manifest | no |
| exemplar | nearest golden Plan | no |
| fill | `fill/v1.md`: the slot contract format and examples | yes |
| verifier L4 | `verifier_l4/v1.md` | yes |
| repair | `repair/v1.md` | yes |
| explainer | `explainer/v1.md` | yes |

A change to a prompt records an eval delta (commit prefix `prompt:`). Nothing here is sent to a model in P3's build phase; it all runs on fakes until the owner confirms a paid run (D-08).

## Fail checks

A registry (`api/pipeline/failchecks.py`) gives every refusal a stable code, its layer, a severity (block or degrade), a repair route (a named deterministic repair, a model retry, or none), a one-line hint for the model, and a plain student-facing message. A test scans the verifier and planner sources and fails if any rule string they can emit is missing from the registry, so the registry cannot drift. The pattern packs' "failure modes to avoid" sections are generated from it.

## Micro-components that make generation cheaper

New Kit components, ordered by how much model output each removes. Each follows the PRD 3.4 rules (precondition, signature, accessibility fence, registration suite; science ones also a citation, units, domain, reference and planted bugs).

| Component | Kind | What it removes from the model's job |
|---|---|---|
| `experiment` (Amali card) | pedagogy | The whole problem, hypothesis, variables, procedure and results scaffold, from catalogue fields |
| `resultsTable` and `record` | ui | A results table the student fills from their own runs |
| `graph` | scene | Axes, ticks and curve with a text-equivalent table |
| `reset` | ui | Restoring defaults |
| `stepper` | pedagogy | Step strips with completion tied to live observables |
| `predictCard` | pedagogy | Predict-observe-explain with `when` predicates against live state |
| `hintLadder`, `conceptCheck`, `workedSolution` | pedagogy | Scaffolds as data |
| Scenes bound to observables: `springScene`, `circuitScene`, `tankScene`, `vectorArrow`, `axes` | scene | Drawing code. A scene draws a quantity; it never prints one |
| `select`, `toggle`, `numberInput`, `dragDrop` | interaction | Input handling |
| Manifest `useWhen` for every component | all | Kit retrieval: the kit pack is the 8 to 15 components the Plan needs |

## Scope

**In:** the layers above built on fakes; the Plan model and checks; the fail-check registry; the prompt packs and their assembler; the generation skeletons for simulation and virtual experiment (the rest in P4); the assembler; slot fills with contracts; the pipeline orchestrator with events, repair and the degrade ladder; the loading skeleton in the web shell; the generation micro-components above that the first two skeletons need (the rest in P4); golden and hostile sets for the vertical; a cost projection.

**Out (and why):**
- Any live model call: needs the owner's confirmed amount (D-08).
- Real citations: needs the corpus (P2, local).
- The remaining skeletons and scenes: authored per Environment in P4.
- State deltas (JSON Patch) and a model-visible summary: P6.

## Risks & unknowns

| Risk / unknown | Confidence | Mitigation |
|---|---|---|
| Plans written by a model are often invalid, so plan checks reject most of them | Unknown; cannot be measured on fakes | Schema-constrained output, a repair step before a retry, and the measurement is the first paid run |
| Skeletons are too rigid, so most real questions fall to `custom` slots or Free | Medium | Count `gap` and `custom` rates in traces; they order the Kit backlog (principle 8) |
| The fail-check registry becomes documentation nobody reads | Medium | A test ties it to the code; the packs are generated from it |
| Deterministic assembly makes every Environment look the same | Medium | Skeleton variants per pattern; scenes and tasks vary with the Plan |
| The research is from search summaries, not primary pages | High | The research note says so and lists the pages to read locally |
| The cost and latency benefits are assumed | High that they are | A-4 stays ASSUMED until the first paid run measures them |

## Definition of done

- A Plan for each of the three Physics Form 5 topics, written by hand as a fake planner output, passes the plan checks, assembles into HTML with no model call, and is minted by the real verifier.
- A Plan with an unknown model, an out-of-domain parameter, an unbacked number or a missing component is refused at the plan checks with the registered code and never reaches assembly.
- A `custom` slot fill that violates its contract is refused at the slot, not at the page.
- Every rule string the verifier and planner can emit is in the fail-check registry (a test proves it).
- The prompt packs load, validate, assemble within their token budgets, and keep a byte-stable cached prefix.
- The pipeline runs end to end on fakes, emits plan and progress events, degrades through every rung of the ladder under injected failures, and the web shell draws the loading skeleton from the Plan.
- A projected cost per Environment, as a range with its assumptions, is written for the owner. No paid call has been made.
