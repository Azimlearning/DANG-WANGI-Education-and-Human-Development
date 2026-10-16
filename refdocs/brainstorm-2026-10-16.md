# Synapse v4: direction brainstorm (founding context)

> Date: 2026-10-16. Owner: Azim (sole author). Written for Azim and for the future Claude sessions that build from this.
> Status: **every decision here is a proposal** until `refdocs/changelog/DECISIONS.md` records it. Where the interview or a measurement disagrees with this file, this file loses.
> Self-contained on purpose: this folder becomes its own repository, so nothing below depends on a relative path outside it. Sources are cited by repo, path and commit (section 11).
> Evidence labels: **READ** (I opened the file or code), **MEASURED** (a number from a result file in a source repo), **PRESS** (secondary coverage, primary not opened), **ASSUMED** (my inference, unconfirmed).
> Writing rule for everything in this repo: no em dashes, no en dashes. Commas, colons, new sentences, and "to" for ranges.
>
> **Read Amendment A1 first.** The interview on 2026-10-16 changed the central design choice (raw HTML stays primary). Sections 1 to 5 still hold for Relations, evidence, verification strength, the trust ladder and the Arcana ports. Sections 4.1 to 4.7 describe a data-first design that A1 supersedes, and are tagged where they conflict.

---

## Amendment A1 (2026-10-16, interview): raw HTML stays primary; Mark 3

**Where this file disagrees with the interview, the interview wins.** The owner's answers, quoted exactly (spelling kept):

> Raw HTML: "I agree with raw html stay primary like in v3 and that makes it more adaptive and generative however u can look into how openai does the inteligent ui feature my idea is having a pipeline with prepade promps, hundreds of micro-compenets since we know our topics and fields, and other funtions to help generation more fast, cost saving and efficient, aracana v2 haa a pipeline or system for the gen ui which is at version mark2 we can enhance and make mark3"
> Stack: "You can decide fully, just which ever one is faster especial for the raw html components"
> First slice: "Let the census decide"
> Git: "I think eotger one or two is good its just that later i will only open the v4 project file so no other fill will be affected"

**The contradiction, quoted and resolved.** Section 0 item 3, section 4.7, section 6.4 and constraint 7 of this file said raw generated HTML belongs in an authoring lane only, and the recommendation to Q2 was "Off". That is **superseded**. The owner's idea is stronger on adaptivity, and it is compatible with most of the rest of this file because the micro-component Kit takes over the job the data-first Runtime was going to do. What changes is *what the generator emits* and *where correctness is enforced*.

| Where | Said | Now |
|---|---|---|
| §0 item 3, §4.1, §4.2 | The Environment is data first, code is a gated exception | The Environment is a **raw HTML/JS document assembled over a vetted micro-component Kit**. The structured plan (the old "spec") is the intermediate representation, not the deliverable |
| §4.4 Parts | Our UI components rendered by a fixed Runtime | **Micro-components**, hundreds, shipped as a versioned same-origin Kit that the generated HTML calls |
| §4.7 authoring lane | Raw HTML only at authoring time | Raw HTML is the runtime output. An authoring lane remains, for *growing the Kit* from repeated gaps |
| §6.4 rejected | "Raw generated HTML at runtime in front of students" | Withdrawn |
| §7 constraint 7 | Raw generated code never reaches a student | Replaced by the lane and label rules in A1.6 |
| §9 Q2, Q3, Q4, Q6 | Recommendations | Decided: Q2 raw primary; Q3 Python API + Next.js + a JS Kit (the agent's call, A1.8); Q4 the census decides; Q6 init here and ignore in the monorepo |
| v3 hard rule 4 and the v4 plan's D1 | "No predefined component library", contradicted by shipped builtin labs | Resolved by this decision: **micro-components are allowed building blocks**. Whole pre-built labs are library *outputs* (cache and builtin), never templates the generator must copy |

### A1.1 What "Mark" means here

| Mark | Where | What it is |
|---|---|---|
| 1 | Synapse v3 | One planner call, one generator call writing a whole HTML document from three worked examples, an LLM verifier with retries, a post-processor, a delivery gate |
| 2 | Arcana v2 (READ) | The generation pipeline of D-31 (template, fences, checking, save, reuse), VerifiedLab and its lifecycle (D-36, D-41), and the compiled-vault plan literally named `genui-obsidianmark2` (D-35). Arcana's own docs use "Mark 2" for the vault direction. "GenUI pipeline Mark 2" is the owner's phrase for the pair |
| 3 | Synapse v4 (this repo) | Mark 1's raw-HTML generation, restructured around a Kit, prompt packs and accelerators, keeping Mark 2's lifecycle, planted-defect discipline and compounding library |

### A1.2 Three lanes

The lane is decided by **what verification the output survives**, not by what the generator intended. A Compose attempt that fails the Kit-provenance check is relabelled `model-checked` or retried.

| Lane | What the LLM writes | Cost and time | Trust label | When |
|---|---|---|---|---|
| **Instantiate** | Nothing, or a small fill (labels, ranges) | About zero to one small call; seconds | `kit-verified`, and `reviewed` or `canonical` once audited | A library hit or a stored composition covers the pattern |
| **Compose** (primary) | Raw HTML/JS that *calls the Kit*: layout, glue, custom scene pieces | One generator call with a short output | `kit-verified` when every displayed number comes from a Kit science micro-model and the assembly checks pass | Default for a new question |
| **Free** | A whole raw HTML document with no Kit, v3 style | v3-like: tens of seconds, about $0.19 | `model-checked`, an honest weaker label. Never `canonical` without human review. Feeds the Kit gap backlog | The Kit cannot express it |

### A1.3 The Kit: hundreds of micro-components

A micro-component is the smallest reusable, versioned unit with an id, a signature, a written precondition, an accessibility fence, tests, and documentation short enough to put in a prompt.

| Kind | Examples | Carries truth? | Registration requires |
|---|---|---|---|
| ui | slider with live value, readout tile, reset, steps strip, study-note card, hint ladder, callout | no | a11y suite, 360 px layout test |
| scene | axes and ticks, vector arrow, beaker, burette, flask, spring, lens, ray, ripple, membrane, particle field | no | render test, no overflow at 360 px |
| interaction | pointer-events drag token with drop target, swirl detector, valve knob, eye-level parallax | no | gesture test in a real browser, touch and keyboard path |
| **science** | `mechanics.projectile`, `mechanics.hookes`, `gas.boyle`, `chem.titration_curve`, `chem.ph_from_h`, `bio.osmosis_flux`, `bio.enzyme_rate`, `genetics.punnett` | **yes** | textbook citation, units and domain, hand-written reference, properties, mutation suite |
| pedagogy | predict card, concept check, misconception probe, worked solution, Amali results table and report skeleton | no | behaviour test; `when` predicates resolve against live observables |
| bridge | ready, event, error, model-visible summary | no | protocol test (MCP-Apps-shaped) |

"Hundreds" is a target, not a count. A rough size, **ASSUMED**: about 40 ui, 120 scene, 25 interaction, 150 to 250 science for the 53-topic syllabus, 25 pedagogy. The P0 census replaces this guess.

```html
<script src="/vendor/kit/1.0.0/core.js"></script>
<script src="/vendor/kit/1.0.0/mechanics.js"></script>
<script>
  const env   = Kit.environment({ title: "Projectile Motion", note: PLAN.study_note });
  const angle = env.slider({ id: "angle", label: "Launch angle", unit: "deg", min: 15, max: 75, value: 45 });
  const speed = env.slider({ id: "speed", label: "Launch speed", unit: "m/s", min: 5, max: 30, value: 20 });
  const shot  = Kit.mechanics.projectile({ angle, speed });          // science micro-model, returns observables
  env.stage(Kit.scene.arena({ trajectory: shot.path, marker: shot.position }));
  env.readout({ label: "Range", unit: "m", value: shot.range });      // must be an observable
</script>
```

An API sketch, not a schema. Properties that matter: values are reactive **observables**; `readout` accepts only observables; science micro-models expose their textbook citation and domain, so provenance and "break it" come for free. The Kit is semver-versioned, and every stored environment records the Kit version it was verified against, so a Kit bump marks environments stale until re-verified (Arcana v2 D-41).

**Why this saves tokens (READ).** v3's generator prompt (version 8) carries three full worked examples. In Example 1 (175 lines) the `<style>` block alone is 36 lines, and `bridge()`, `fail()`, control wiring and the reset handler recur nearly verbatim in all three examples. The model re-writes that chrome on every generation. In Mark 3 it becomes calls.

### A1.4 Prompt packs

v3's generator prompt is one monolith (Blocks A to D, three fixed examples). Mark 3 assembles it:

| Segment | Content | Chosen by | Cache |
|---|---|---|---|
| core | goal, hard rules, bridge contract, accessibility, size cap | fixed | stable prefix, cached |
| pattern pack | rules and one exemplar for: simulation, virtual experiment, explorable diagram, data viz, drag-drop, process stepper, exam practice, Amali bench | router output | cached per pattern |
| kit pack | signatures and one-line docs for only the 8 to 15 relevant micro-components, retrieved by topic and quantities | Kit retrieval | per request, small |
| exemplar | the one or two nearest golden compositions, not three fixed | nearest topic and pattern | per request |
| plan | the structured plan: title, quantities, governing relations by id, tasks, study note, steps | planner | per request |

Prompt packs are files in git, versioned, and every change records an eval delta (v3's rule). A/B comparison runs through the eval harness.

### A1.5 Accelerators ("functions to make generation faster, cheaper, efficient")

| # | Function | What it does | Saves | Exists today |
|---|---|---|---|---|
| 1 | Library lookup | canonical key (topic id and concept), then embedding nearest; serve a stored environment, re-verified before serving | the whole generation | v3 Phase 4 plan, v2 D-41 |
| 2 | Template instantiate | fill a stored composition for a covered topic and pattern | tens of seconds | new |
| 3 | Edit, not regenerate | for near hits ("add air resistance"), send the stored script plus a delta and ask for a diff | tokens and time; MAIC-UI reports edit cycles of 200 to 600 s reduced to under 10 s with diff-based generation | new |
| 4 | Kit retrieval | inject only the relevant micro-component docs | input tokens as the Kit reaches hundreds | new |
| 5 | Model tiering | router and planner on a small model, generator on the strong one, verifier small | dollars | v3 partly |
| 6 | Prompt caching | stable prefix cached; Kit pack and exemplar kept small so the uncached tail is short | input dollars | v3 has |
| 7 | Skeleton first | render chrome (title, note, layout, controls from the plan) immediately and hydrate when generation completes | perceived latency | v3 streams code; this is new |
| 8 | Early gates | scan, then Kit-provenance lint, then a 3 s render smoke, and only then the LLM verifier | wasted verifier calls | v3 has scan and render; lint is new |
| 9 | Deterministic repair | a failure class seen three times becomes a post-processor rule or a Kit-level guard | retries | v3 has |
| 10 | Output budget | `max_tokens` set per pattern; an over-budget Compose answer is retried or routed to Instantiate | tail cost | new |
| 11 | Overnight fill | batch generation of uncovered syllabus topics, audited next morning | student waiting | v4 plan N9 |
| 12 | Question canonicalisation | the local router plus normalisation raises the hit rate | LLM calls | v3 shadow router exists |
| 13 | Per-request budget and degrade | over budget falls back to Instantiate or text | a dollar ceiling | new; v2's spend seam |

### A1.6 Verification, honest version

| Layer | What | Lane | Exists |
|---|---|---|---|
| L0 | Forbidden-API scan, CSP injection, size cap, single document | all | v3 post-processor (READ) |
| L1 | **Kit provenance**: every `<script src>` is a pinned Kit bundle or an allowlisted vendor library; `readout` arguments are observables; control-derived arithmetic outside Kit calls is counted. Dynamic: numeric text in readout regions is probed against Kit observables | Compose | new |
| L2 | Render and fuzz: ready within 5 s, controls wired, no uncaught error, reset works. **Extend** with grid and extreme values (the solvability idea in Google's learning interactives) | all | v3 harness |
| L3 | **Numeric cross-check**: the harness drives controls to grid and extreme points and compares displayed values with the science micro-model's own reference, evaluated independently | Compose | new |
| L4 | LLM verifier: pedagogy, labels against units, expected behaviours, spot checks | all; the only science check in Free | v3 |
| L5 | Mint and gate: only the verifier can mint; the gate re-hashes and re-checks | all | v3 (READ) |
| L6 | **Planted-physics-bug suite** run against the verifier itself, to produce a detection rate | process | new (v4 plan N2) |

What is and is not guaranteed:

- **Compose, L0 to L5:** the numbers shown come from audited micro-models, and the assembly works across the tested grid. **Not guaranteed:** that the *scene tells the truth*. A correct number beside a misleading picture is caught only by L4 and review.
- **Free:** model-checked only, the same strength as v3, and unmeasured. Labelled so.
- **Science micro-models:** only as good as their reference and review. The oracle problem (section 4.8) now applies *here*, one level down. A micro-model is audited once and reused hundreds of times, which is the point.

Revised constraint 7: *Raw generated HTML may reach a student only after the full verification of its lane, carrying the honest trust label of that lane. Free-lane output is never `canonical` without human review, and every Free generation is logged as a Kit gap candidate.*

### A1.7 Cost: arithmetic, not measurement

v3 measured about $0.19 per artifact including retries, 3k to 9k output tokens, 60 to 90 s. Arcana v2's priced table lists Sonnet 5.5 at $2 input and $10 output per million tokens (confirmed by its cost auditor, 2026-10-07). So 6k output tokens is about $0.06 of the $0.19, and the remainder is input, retries and the verifier (not decomposed). If Kit composition brings output to 1k to 2.5k tokens, the output term is roughly $0.01 to $0.025 and the retry term falls with it. This is a **hypothesis**. The P3 definition of done measures it.

### A1.8 Stack, decided as asked ("whichever is faster, especially for the raw html components")

**Python API (FastAPI, uv) + Next.js web (pnpm) + `packages/schema` (TypeScript, codegen to Pydantic) + `packages/kit` (the micro-component library, plain TypeScript built by esbuild, tested by vitest).**

Why this is the faster path for raw HTML:

- The raw-HTML pipeline already exists, tested, in Python: post-processor, scan, verifier, delivery gate, render harness, router, evals, SSE. Rewriting it in TypeScript is the slow path.
- Arcana v2's lifecycle, mint, store and mutation harness are Python and port directly.
- The ingestion and router-distillation assets are Python.
- The Kit is the only large new JavaScript surface, and it builds and tests under pnpm independent of the API language. It is served as static files from `/vendor/kit/<version>/`, which is exactly the v3 same-origin library rule.
- Node becomes a **build and test** dependency only, not a runtime kernel executor. Verification runs generated HTML in headless Chromium (Playwright, already Python-friendly), which resolves the "Node as a runtime dependency" caution in section 2.5.
- Isolation for a public deploy is a headless-browser container with no network. A P1 spike confirms it.

Rejected for speed: TypeScript end to end. Its one real benefit (a single evaluator shared by verifier and browser) matters less once science lives in Kit micro-models that the browser and the harness both load from the same bundle.

### A1.9 What OpenAI-style gives Mark 3

| OpenAI pattern | Mark 3 use |
|---|---|
| A design-system library (`@openai/apps-sdk-ui`, ChatKit nodes) so components look native | The Kit's ui and scene micro-components. Fixes v3's logged problem that artifacts clashed with the shell |
| One component per tool, display modes, "use UI only when it helps" | Presentations (section 4.5) and the router's `text_only` exit |
| Actions back to the model; `modelContent` versus `privateContent` | Bridge events with a model-visible summary and UI-private detail |
| Adjustable curated modules for common concepts | The Instantiate lane's library |
| "Complete the path", "explain limits" | Honest degrade with a next step |
| Declared CSP compared with behaviour at review | The environment manifest audit (idea B-13) |

### A1.10 New risks from this decision

| Risk | Mitigation |
|---|---|
| Correctness is weaker than the data-first design, especially in the Free lane | Lane labels are honest and visible. L3 and L6 produce numbers instead of claims. Free is never `canonical` |
| The generator bypasses the Kit and re-implements physics | L1 and L3 detect it; a bypass drops the output to the Free label |
| Authoring hundreds of micro-components, each with tests and, for science, review | Interaction-pattern parameterisation; the gap backlog orders the work; the Kit grows only on measured demand |
| Kit API churn invalidates stored environments | Semver, version recorded per environment, stale on bump, re-verified on reuse |
| Prompt packs drift without an eval | Every pack change records an eval delta; golden and hostile sets are hash-pinned |
| The Kit becomes the v1 "12 concepts" ceiling again | Free lane stays open and every Free output is a gap candidate |

---

## 0. The short version

1. **What Synapse is for.** Give a Malaysian Form 4 or 5 KSSM student an **environment**: a bounded interactive world they act in, where a *verified model of the science* responds, with a task and the textbook evidence beside it. A lab is one kind of environment. A chart or a chat answer is not.
2. **Four builds each solved one part and dropped the rest.** v1 had pedagogy. v2 had safe generated formulas. v3 had free generation behind a delivery gate. Arcana v2's lab tier added exhaustive verification and a governed lifecycle. None of them composes *rich* environments safely.
3. **The core idea: stop generating the whole artifact.** Separate what is **true** (a curated Relation Registry and the Model composed from it), what is **seen** (Parts: our own vetted components, grouped in Kits), what is **asked** (Tasks and Scaffolds), and what **runs** it (one fixed Runtime). The LLM designs by *composing* these. So most environments are **data, not code**. Generated code is a gated exception. ~~Raw generated HTML enters only at authoring time, never in front of a student.~~ **Superseded by A1: raw HTML stays primary, assembled over a micro-component Kit.**
4. **"Extensive GenUI components" means the Part library.** Parts are parameterised by interaction pattern (v1's D-02), admitted only with a written precondition and a planted-defect suite (Arcana v2's D-31). The library is the moat and the main body of work.
5. **The field is converging on this shape, and generic sims are being commoditised.** OpenAI ships typed widgets with display modes and, per press, 70+ adjustable math and science modules free to all users (March 2026). Google ships teacher-vetted learning interactives (17 Sep 2026). Synapse's reason to exist is what they will not do: exact KSSM scope and page citations, Bahasa Melayu, SPM practical and exam modes, phone and offline reach, and verification you can inspect.
6. **Take from Arcana v2:** lifecycle table, contract, verifier and mint, delivery gate, mutation harness, fixed host template, spend ledger, verbatim-quote checks, mastery rule, evaluation discipline. **Leave:** graph retrieval (measured: no gain), the agent roster, the single-user assumptions, `node:vm` as isolation.
7. **The hardest unsolved problem is the oracle**: what independent thing says the model is *true*. Section 4.8 sets out a ladder and the one research bet worth making (textbook worked examples as reference cases).
8. **No deadline.** Sequence by dependency and evidence, not by date. The decisions that gate scaffolding are in section 9.

---

## 1. Framing: "environment"

### 1.1 Why "environment" and not "lab"

- "Lab" promises an experiment. KSSM students also need a **process explorer** (transcription, digestion), a **data investigation**, a **worked-problem room** for SPM questions, and a **practical bench** (Amali). One word that covers all of them is better than five.
- It names the right thing to build: the student *acts inside* something and it *responds*. That is a microworld in Papert's sense and an exploratory learning environment in the simulation-learning literature (ASSUMED recall, **verify before citing**: Papert, *Mindstorms*, 1980; de Jong and van Joolingen, *Review of Educational Research*, 1998).
- It points the engineering at the whole (model, scene, task, evidence) instead of at one numeric function, which is where Arcana v2's "lab" stopped.

### 1.2 Definition

An **Environment** is a verified, bounded, interactive space for one learning goal. It has:

| Element | Plain meaning | Who produces it |
|---|---|---|
| **Model** | The declared science: quantities, relations, constraints. The only source of numbers. | Composed from the Relation Registry; kernel glue only if unavoidable |
| **Scene** | What the learner sees and manipulates. | Parts from our library, bound to Model quantities |
| **Instruments** | Ways to observe the response: readouts, plots, tables, gauges. | Parts |
| **Task** | What the learner is asked to do: predict, observe, explain, record, challenge. | Planner, from templates |
| **Scaffolds** | Hint ladder, worked solution, formula toolbox, misconception probes. | Planner plus the misconception KB |
| **Evidence** | The textbook statements the Model rests on, and the checks it passed. | Retrieval plus the verifier |

### 1.3 What it is not

- Not a chat answer with a chart attached.
- Not a video-style world model (Genie class). Section 3.4.
- Not an arbitrary generated web app.
- Not a workspace over a user's own documents. That is Arcana.

### 1.4 Glossary (use these words consistently, in code too)

| Term | Meaning |
|---|---|
| Environment | The learner-facing artifact, delivered only as a verifier-minted type |
| Model | A typed dataflow of Quantities and Relations, plus optional stepped state |
| Quantity | A named, unit-bearing, range-bounded value (mass in kg, 0.1 to 5) |
| Relation | A curated, evidence-cited rule over Quantities: an equation, a law (sign or monotone trend), a process (ordered stages), or a fact |
| Registry | The reviewed set of Relations, each with a reference implementation and a textbook citation |
| Part | One vetted UI component (Slider, Plot, Beaker, OsmosisTank) |
| Kit | A named family of Parts for a domain (Mechanics, Titration, Cell) |
| Binding | A typed link from a Part's input or output to a Quantity |
| Kernel | A small generated pure function in the restricted JavaScript subset, only when composition cannot express an operation |
| Contract | What the verifier checks a Model or Kernel against: reference cases, properties, reference implementation |
| Mint | The single place that can create the deliverable type |
| Gate | The delivery path that re-derives, re-hashes and re-checks the stored record |
| Presentation | How an Environment is shown: Peek, Stage, Companion, Shelf |

### 1.5 Naming hazards

"Environment" collides with environment variables, virtualenvs, RL environments and Environmental Science. Rule: in code `Environment` is the learner-facing artifact only. Configuration is called *settings*. Never abbreviate it to `env`. The "Synapse" name has its own collision (a published 2026 paper uses SYNAPSE for an AI tutor). Both are flagged in section 9.

---

## 2. What the earlier builds give

### 2.1 Four builds

| | v1 `Synapse/` (1 Jul) | v2 `synapse-v2/` (15 Jul) | v3 `Synapse-V3/` (16 to 18 Jul, active to Sep) | Arcana v2 lab tier (8 to 15 Oct) |
|---|---|---|---|---|
| Generative level | 1: select and configure pre-built components | Tier B: the model designs a sim as data in a restricted expression grammar; A: pinned sims; C: raw HTML | 3: the model writes the whole HTML/JS lab | 3, narrowed: one generated pure function in a fixed template |
| Safety mechanism | Faithfulness pinned in component code | No `eval`; `when` conditions computed at run time; pins merged over model output | Type only the verifier can mint; sandbox, CSP, scan layers; LLM verifier | AST allowlist, then exhaustive execution of every slider setting against a Python reference; mint; gate re-derives and re-hashes |
| Pedagogy | Sourced misconception KB, strategy, tutor loop, spaced repetition | Premise checker, guide reacting to values | Explainer note only | Cloze quiz and mastery (from the vault), not tied to labs |
| Coverage | 12 concepts | Anything the sim grammar can express | Anything, 60 to 90 s, ~$0.19 per artifact (v3 evals) | 4 hand-written contracts, none physics |
| Carry forward | Misconception KB, learner model, POE framing | `when` principle, pins, expression grammar idea | Pipeline, evals harness, router distillation, 53-topic KSSM taxonomy, 1,971 ingested passages | Everything in section 5 |

### 2.2 What Arcana v2 added over Arcana v1 (READ at commit `21c6dcf5`, 2026-10-16)

| Area | v1 | v2 | Relevance to Synapse |
|---|---|---|---|
| Roster | Many agents (21, 24 and 25 are all quoted in different documents; not recounted) | 6 agents: Orchestrator, Research, Graph, Fact Checker, Composer, Studio; capability grows as typed tools (D-30) | Take the rule, not the roster: an agent exists only for a distinct trust boundary, state or terminal duty |
| Wire | Loose | One schema in TypeScript, codegen to strict Pydantic, drift check, fail-closed validation (D-19) | Take as is |
| Layout | Fixed modes | `LayoutSpec` v2: panels with regions, prebuilt Basic first, Adaptive layered on, saved views, panes (D-27, D-28, D-32, D-44) | Take the idea: layout is data owned by the Composer |
| Components | 24, partly decorative | Catalog entries with a written structural precondition, caps, a11y fences, placement hint, registration suite of planted defects (D-29, D-31) | Take as is. This is the Part discipline |
| Graph | Free-form extraction | Atomic-note graph, compiled vault (concept pages, links, claims, lint) (D-34, D-35) | See 2.4: keep the *notes and claims* layer, drop graph retrieval |
| Learning | Not built | Cloze quiz from claims (no model), mastery rule, review schedule, insights, flashcards | Quiz and mastery port. Studio breadth does not |
| Generated code | Not built | VerifiedLab: contract, checker, verifier, mint, gate, fixed template, lifecycle (D-36, D-41) | The keystone |
| Trained models | Spec only | One pretrained re-ranker tried, not shown to help (D-37); no router built | Synapse keeps its own router work |
| Scale of evidence | None | 1,627 backend and 459 web tests, 120 planted defects, 38-question benchmark with protocol fixed first | Take the discipline |

### 2.3 The v2 GenUI pipeline, stage by stage (D-31, D-36, D-41)

Five stages for every UI the system makes: **template, fences, checking, save, reuse**. For generated code (P4) the stages become:

1. **Contract.** At most four parameters on a fixed grid, a source phrase that must occur in a stored passage, hand-written reference cases, properties (finite, bounded, monotone, matches reference).
2. **Evidence gate.** No stored passage states the formula, then the lab is `empty`. Never invented.
3. **Generate.** One short function, one call through the spend seam. The model sees the passage and the parameters, *not* the reference cases.
4. **Check.** An `acorn` AST allowlist: numbers and booleans only, a fixed `Math` list, bounded loops, no property access outside the list.
5. **Verify.** Run every grid combination (up to 10,000) plus a seeded fuzz of 200, in a Node child process, against a Python reference. Mean call 5 ms, no call over 250 ms.
6. **Mint.** Only the verifier module can construct `VerifiedArtifact`. A closure-held token, no subclassing.
7. **Gate and render.** The store ties id to hash. The gate re-derives the block from the stored record and re-checks it. The browser re-hashes. A template *we wrote* renders in `sandbox="allow-scripts"` with `default-src 'none'`.

The reusable ideas, ranked by how much they teach beyond "sandbox it":

- **Verify what the interface can reach, not a sample.** A red-team review found a source that matched a 603-vector sample and froze at one slider position. The fix made the slider positions a fixed grid and verified all of them. *What was verified is exactly what can be asked.*
- **Reuse re-verifies.** A cached lab runs `verify()` again before it is served. Transient failures (`run` stage) never evict.
- **A template cannot register unless its planted defects are all rejected.**
- **The gate does not trust the store.** It re-hashes.

### 2.4 "Mark 2": the vault (D-35), and what it actually showed

Mark 2 is a compiled vault over the graph: concept pages above nodes, asserted and co-mention links, claim notes, a notes view, a learner layer, lint. **MEASURED** across five pre-registered looks on the same 19 questions:

- The vault strengthens its own graph signal (full corpus, +0.034 nDCG@10, p = 0.52) but not the fused result (no change, p = 0.57), and sits 0.026 below the baseline free-form hybrid (p = 0.11).
- Graph retrieval is not shown to beat flat over 38 questions (pooled -0.001 nDCG@10, p = 0.69).
- The vault's own conclusion: its case is **notes, claims, quiz and mastery, not retrieval gain**.

**Consequence for Synapse:** retrieval over a fixed, small, curated textbook corpus is flat hybrid (BM25 plus dense) with a topic taxonomy for routing. The part of Mark 2 worth porting is the *claims* idea: sentences a passage states, kept verbatim, usable as evidence and as cloze questions with no model call.

### 2.5 What does not transfer

| Arcana v2 choice | Why it does not carry to Synapse |
|---|---|
| Single user, no auth, no rate limit (D-04) | Synapse is public. Needs per-session limits and a cost ceiling |
| `node:vm` in a child process | v2's own docs say it is not isolation. A public deploy needs a container with no network and resource limits, or a WASM engine (spike in P1) |
| One pure function of at most 4 numbers to 1 number | Cannot draw, drag, animate or step. Synapse's titration and orbit labs need more |
| Four hand-written contracts, all retrieval formulas | Open questions need a contract nobody has written. This is the oracle problem |
| Evidence = the user's own papers | Evidence here is a fixed curated corpus the product owns |
| Node as a runtime dependency | Synapse-V3's backend image is `python:3.12-slim` with no Node (READ) |
| Graph retrieval, Studio writing tools, agent roster | Not Synapse's job, and the measurement says no gain |

### 2.6 Corrections to the analysis handed in on 16 Oct (so they are not inherited)

| Claim as handed in | What the source says |
|---|---|
| "About $0.003 per lab" | **MEASURED** $0.0458 for 15 paid generation calls, so ~$0.003 *per call* for a ~700-token function, routed through OpenRouter because Anthropic credit was exhausted. A full Environment spec plus kernels is several times larger. **Unmeasured.** Do not quote $0.003 as the cost of an environment |
| "6 of 8 first attempts accepted" | After one prompt revision. The first prompt scored 2 of 8. Reported beside, never instead |
| "F1@k failed, the gate refused it" | True, and it is the most instructive result: the model implemented F1 from the passage faithfully, and the *contract* demanded a clamp the passage never states. The verifier tested the contract author, not the model. This is the oracle problem in miniature (4.8) |
| "About a third of the 53 topics fit" | My own earlier estimate (about 11 of 13 Physics, 3 to 4 of 13 Chemistry, 2 to 3 of 27 Biology). **Never measured.** P0 runs a coverage census |
| "Items 1 to 4 are the main prize" | Agreed, with the generalisation in section 5 (scalar to multi-output and stepped) |

---

## 3. The outside field (checked 2026-10-16)

| Source | What it is | Take | Do not take |
|---|---|---|---|
| **OpenAI Apps SDK UI guidelines** (official) | Inline card, inline carousel, fullscreen, picture-in-picture. Inline cards: at most two actions, no tabs, no deeper navigation, no nested scrolling. Carousels: 3 to 8 items. "Use only when it helps", "stay native", WCAG AA, system fonts | Presentation modes (4.5). The restraint rules for the Peek card. Accessibility as a floor | Their visual style, which is deliberately platform-neutral |
| **OpenAI UX principles** (official) | Add UI only when visual interaction materially improves the workflow. Complete the path. Tie tools to user goals. Explain limits and offer a next step | "Complete the path" and "explain limits" are exactly the honest-degrade rule | Nothing |
| **OpenAI Apps SDK components** (official) | UI is an MCP resource (`ui://`, MIME `text/html;profile=mcp-app`) in a sandboxed iframe, JSON-RPC over `postMessage`: `ui/initialize`, `ui/notifications/tool-result`, `tools/call`, `ui/message`, `ui/update-model-context`. Widget state splits `modelContent` (model sees) from `privateContent` (UI only). CSP declared in metadata and compared with behaviour at review. Treat `structuredContent` as untrusted | Bridge protocol shaped like MCP Apps so Environments *could* be served inside ChatGPT or Claude later (cheap now, hard to retrofit). The `modelContent` / `privateContent` split for what the tutor may see. Declared manifest compared with behaviour at audit | `window.openai` extensions (checkout, file upload). Not needed |
| **OpenAI ChatKit widgets** (official) | One `WidgetRoot` (Card, ListView) containing `WidgetNode`s: Box, Row, Col, Form, Spacer, Divider, Text, Title, Caption, Markdown, Badge, Icon, Image, Button, Select, DatePicker. Actions (`onClickAction` and friends) go to your backend. Streaming flags on Text and Markdown. No chart node documented, and no validation mechanism documented | The *shape*: a closed typed vocabulary, one root, actions as data. Streaming flag | Static cards with actions are not environments. They have **no live model binding**. Bindings are the thing Synapse adds |
| **ChatGPT interactive visual explanations** (PRESS: TechCrunch, Engadget, Campus Technology; OpenAI's own post returned 403) | Launched 10 Mar 2026. 70+ math and science topics (Ohm's law, Hooke's law, Charles' law, Coulomb's law, exponential decay and others), adjustable variables, free to all users per press | Confirms the market expects adjustable modules, and that a library is the unit. **Press does not say whether they are pre-built or generated per request** | Do not compete on "an interactive physics widget exists". It does, free, for English-language generic content |
| **Google learning interactives** (blog, 17 Sep 2026; arXiv 2609.20738, abstract only) | Teacher picks a topic, objectives are proposed, Gemini generates game-like interactives with levels, formula toolbox, multi-level hints, worked solutions. Agentic auto-evaluation including **solvability checks that simulate a user and try adversarial extreme parameter values**. Every released item is teacher-vetted. US pilot, 12 teachers, mean 8/10 | Scaffold vocabulary (hint ladder, formula toolbox, worked solution). Adversarial extreme-value probing, which our exhaustive grid supersedes for closed-form kinds | Reliance on teacher vetting and agentic eval as the *only* correctness story |
| **Vercel json-render** (Jan 2026, Apache-2.0; secondary write-ups only) | Zod catalog of components fed to the model, flat JSON spec (root plus element map) streamed back, validation gate, registry maps to implementations | Flat element map (resilient to partial streams). Catalog-to-prompt generation from one schema | Do not adopt wholesale: no bindings, no mint, no hash gate. Spike it as a renderer foundation only if it earns its place |
| **Google A2UI**, **AG-UI**, **MCP Apps** (earlier research pass, 2026-07-06 and today) | Declarative UI protocols and an agent-to-app event protocol | Wire discipline: UI as data, events upstream | Nothing to adopt now |
| **Genie 3 class world models** | Generated interactive video-like worlds. One press-reported limit: coherence around a minute. A 2026 benchmark scored Genie 3 66.67 on physics with no verified accuracy measure. No published education study found | Nothing | They cannot be verified, which is the whole point. Rejected as an environment generator |
| **PDE-grounded intent verification** (arXiv 2605.09360) | Reconstructs the governing equations from generated simulation code and scores them against an intended contract. Execution-only repair left 39 to 40 percent of 220 cases runnable but solving the wrong physics | The argument for a *declared* model checked against an *independent* reference, not execution success | Their MOOSE-specific machinery |

### 3.1 What this means

- **Generic interactive sims are commoditised.** Differentiate on: exact KSSM scope with page citations; Bahasa Melayu and bilingual SPM; the practical (Amali) bench and exam-mirror modes; phone-first and offline; forwardable single files; verification a student or teacher can inspect.
- **The vetted library is the industry pattern**, from OpenAI's modules to Google's teacher-approved items. Synapse's library is verifier-minted and re-verified on reuse, which is a stronger claim than "a teacher looked at it".
- **The Neshaei objection** (runtime GenUI cannot be verified at scale, so author at design time) is answered structurally: generate at *authoring* time for new parts and relations, compose at *request* time from audited ones.

---

## 4. The core design

> **A1 note.** 4.1 to 4.7 describe the data-first design the interview changed. Still valid: the five separations as a way of thinking, model kinds and verification strength (4.3), presentations (4.5), the oracle problem and ladder (4.8), the trust ladder (4.9). Superseded: the Environment Spec as the deliverable (4.2), a fixed Runtime rendering Parts (4.4), and the authoring-only lane (4.7). Read them with "Part" meaning "micro-component" and "Spec" meaning "plan".

### 4.1 Five separations

```
EVIDENCE   what the textbook states            (retrieval, verbatim quotes)
MODEL      what is true                        (Relations composed into a dataflow)
SCENE      what is seen                        (Parts bound to Quantities)
TASK       what the learner is asked           (predict, observe, explain, record)
RUNTIME    what runs it                        (one fixed host, written by us)
```

The LLM touches EVIDENCE only through retrieval, MODEL only by *choosing and wiring registered Relations*, SCENE only by *choosing Parts and bindings*, TASK by filling templates. It never writes the Runtime. It writes Kernel glue only when composition cannot express an operation, and that glue goes through the full gate.

### 4.2 The Environment Spec (a sketch, not a schema)

```jsonc
{
  "id": "hookes-law-extension-0001", "specVersion": 1,
  "topic": { "kssm": "<id from the 53-topic taxonomy>", "subject": "physics", "form": 4 },
  "evidence": [ { "chunkId": "...", "doc": "...", "page": 0, "quote": "<verbatim span>" } ],
  "model": {
    "kind": "closed_form",
    "quantities": [
      { "name": "load",      "unit": "N",  "min": 0, "max": 10, "default": 2, "grid": 40, "role": "input" },
      { "name": "k",         "unit": "N/m","min": 10,"max": 100,"default": 40, "grid": 18, "role": "input" },
      { "name": "extension", "unit": "m",  "role": "derived" }
    ],
    "relations": [ { "ref": "hookes_law", "bind": { "F": "load", "k": "k", "x": "extension" } } ],
    "claims": [ { "id": "c1", "text": "Extension is proportional to load below the elastic limit.", "evidence": 0 } ]
  },
  "scene": {
    "parts": [
      { "id": "spring", "part": "mechanics.SpringHanger", "bind": { "load": "load", "extension": "extension" } },
      { "id": "plot",   "part": "core.Plot", "bind": { "x": "load", "y": "extension" } },
      { "id": "record", "part": "core.RecordTable", "bind": { "cols": ["load", "extension"] } }
    ]
  },
  "tasks": [
    { "kind": "predict", "prompt": "...", "options": [ { "label": "...", "when": "extension(load=3) > extension(load=2)" } ] }
  ],
  "scaffolds": { "hints": ["...", "...", "..."], "worked": "..." },
  "presentation": { "peek": ["load", "extension"], "stage": "default" }
}
```

Properties that matter:

- **Predictions resolve by a `when` predicate evaluated against the live Model**, never against an answer baked in at generation time (v2's pin principle). A `when` that references no Quantity is rejected as an assertion.
- **Everything is data except an optional Kernel**, which is inert text, hashed, minted, and re-hashed by the browser (v2's one amendment to "the wire carries data only").
- **Remix, personalisation and translation are spec edits**, not regeneration. "Add air resistance" adds a registered drag Relation to the dataflow and re-verifies. A Bahasa Melayu version swaps text fields and leaves the Model untouched, so verification is unaffected. This is a large structural advantage over v3's code-level remix.

### 4.3 Model kinds and how each is verified

| Kind | Typical KSSM content | Verification | Strength |
|---|---|---|---|
| Closed form | Hooke's law, Ohm's law, density, Boyle's law, pH | Exhaustive grid against the registered reference, plus properties (v2's method) | Strongest |
| Stepped | Projectile motion, pendulum, cooling, population growth | Grid over parameters and initial state, fixed step count, against a reference integrator or analytic solution, plus invariants (energy within tolerance, bounds, monotone) | Strong |
| Combinatorial | Punnett squares, titration tables, balancing | Exhaustive enumeration against a reference | Strong |
| Stochastic (seeded) | Diffusion, osmosis, mutation | Seeded runs, statistical properties (net flux sign, symmetry) within stated tolerance over N runs | Moderate. Labelled honestly in the UI |
| Process (staged) | Transcription, digestion, electrolysis steps | State graph: every stage cites a quote, reachability, no dead end | Evidence-bound, not numeric |
| Qualitative | "More solute outside, water moves out" | Sign and monotone properties from registry `law` entries, checked on the running Model | Evidence-bound |

A state vector is a set of **scalar** update functions (`next_x(p, s)`, `next_v(p, s)`). The checker stays numbers-only, so v2's allowlist (no arrays, no strings, no objects) carries over unchanged.

### 4.4 The Part library ("extensive GenUI components")

Parts are parameterised by **interaction pattern**, not topic (v1 D-02). Relations are keyed by topic. Together they give combinatorial coverage without one component per topic.

| Layer | Parts (indicative, not a commitment) |
|---|---|
| **Core** (domain-neutral) | Slider, Stepper input, Toggle, Dropdown, DragToken with targets, Readout (value, unit, significant figures), Plot (multi-series, markers, axes), RecordTable (the Amali results table), Gauge, Stage timeline, Callout (study note), Checklist (procedure), PredictCard, HintLadder, CitationChip, Equation (KaTeX, vendored), HotspotDiagram, SceneCanvas primitives bound to Quantities |
| **Mechanics kit** | Block, Ramp, SpringHanger, Pendulum, Trolley with ticker tape, ProjectileArena, Pulley |
| **Waves and optics kit** | RippleTank, RayBox, Lens, Mirror, WaveString |
| **Heat and gas kit** | GasContainer with particles, HeatingCurve |
| **Electricity kit** | Circuit with fixed topologies, Meter |
| **Chemistry kit** | Beaker, Burette with stopcock, Flask, ParticleView, pHScale, TitrationCurve, ElectrolyticCell |
| **Biology kit** | CellMembrane, OsmosisTank, EnzymeCurve, PopulationChart, PunnettGrid, OrganDiagram, ProcessStepper |

Each Part carries (v2's template record, extended):

1. A **written structural precondition**: which Quantity dimensions it accepts, which Relation kinds it needs.
2. **Typed bindings** (a Plot accepts any two real Quantities; a Burette accepts a volume).
3. **Fences**: caps, a11y requirements (role, label, a text equivalent that carries all the information), phone layout (360 px, 44 px targets, reduced motion).
4. A **registration suite** of planted defects (binding to the wrong dimension, NaN, extreme values, overflow, missing text equivalent). It cannot register until every defect is refused.
5. A **gallery entry** (a Storybook-like page). The gallery doubles as the human audit surface and the visual regression baseline.

**Part gaps are data.** When the Planner wants a visualisation no Part offers, the Composer degrades to the nearest admissible Parts (Plot plus Readout) and records a closed-reason `part_gap`. The gap backlog tells you which Part to build next.

The titration lab already in Synapse-V3 (burette, flask, pipette, eye-level parallax) is the stress test: it should be reproducible as a *Chemistry kit composition*, and any element it needs that no Part offers is a Part to build.

### 4.5 Presentations (taken from OpenAI's display modes)

| Presentation | Use | Rules |
|---|---|---|
| **Peek** | Inline card in the conversation: one live readout, at most one control, one "Open" action | At most two actions, no tabs, no nested scrolling. Must make sense with no network after load |
| **Stage** | Full screen, the Environment is the answer. The composer stays overlaid so the student can keep asking | Phone-first. Chat recedes. Back affordance |
| **Companion** | A small persistent view while follow-up questions are asked (keep the burette while asking why it turned pink) | Updates when the student interacts through the composer. Closes when the task ends |
| **Shelf** | Carousel of library Environments for a topic or chapter | 3 to 8 items, one action each. This is the syllabus library entry point |

### 4.6 Pipeline

| # | Stage | Who | Failure behaviour |
|---|---|---|---|
| 1 | **Route**: topic ids, presentation, `text_only` | Local classifier, LLM fallback below a confidence threshold | Out of syllabus or non-science exits to text |
| 2 | **Evidence**: retrieve KSSM passages, look up Relations | Deterministic | No stated relation, then `empty` with a reason. Never invented |
| 3 | **Admit**: which kits, Parts and model kinds the evidence can support | Deterministic, closed reason list | Drops, never repairs |
| 4 | **Design**: choose Relations, Quantities and ranges, Parts and bindings, Tasks | LLM, forced tool use | Schema failure retries once, then degrades |
| 5 | **Validate**: strict schema, unknown ids refused, units and dimensions, bindings, caps | Deterministic | Refuse |
| 6 | **Kernel**: only if composition cannot express it | LLM, small, restricted JavaScript | Counts as an attempt |
| 7 | **Check**: AST allowlist | Deterministic | Refuse |
| 8 | **Verify**: grids, steps, seeds, properties, reference | Deterministic, isolated runner | Refuse, name the stage |
| 9 | **Mint**: `VerifiedEnvironment`, verifier module only | Deterministic | n/a |
| 10 | **Store and lifecycle** | Deterministic | n/a |
| 11 | **Gate**: re-derive, re-hash, re-check | Deterministic | Never serve on a failed gate |
| 12 | **Deliver**: stream blocks, client re-hashes, fixed Runtime renders in a sandboxed iframe | Fixed code | Honest degrade card |

LLM calls: stage 1 fallback, 4, 6, and the explainer and tutor. Everything else is code with tests.

### 4.7 The authoring lane (where raw generation lives)

Raw generated HTML does not go away. It moves to **authoring time**, where a human is in the loop:

- **Part proposals**: the LLM drafts a new Part (and its registration suite). A human reviews. It enters the library only by passing the registration suite.
- **Relation proposals**: the LLM drafts a Relation from a textbook passage with a reference implementation and properties. A human reviews against the page. It enters the Registry only with a citation.
- **Sketches**: free-form HTML experiments for exploring what a new Part might look like. Never reachable from the student path.

This is what keeps the student path closed while the library still grows, and it is the answer to "does the bound cap the product". The bound is *measured* (part gaps, unregistered relations) and *growable* through a governed lane.

### 4.8 The oracle problem (the hardest part)

The verifier proves a Model matches a **reference**. Something independent must supply the reference, or "verified" only means "internally consistent". Arcana v2 sidestepped this by hand-writing four references. Its own F1@k result shows the failure mode: the contract can be stricter than, or different from, the source.

| Rung | Reference comes from | Independence | Scales | Policy |
|---|---|---|---|---|
| **Registered** | A human-reviewed Relation with a hand-written reference and a textbook citation | High | Slowly: reviewer time | Servable. Eligible for `reviewed` and `canonical` |
| **Evidence-derived** | Reference cases extracted from the textbook's *own worked examples* (printed inputs and printed answers), numbers verified verbatim in the passage | High if extraction is verified | Per passage | **The research bet** (below). Servable if all cases pass |
| **Cross-derived** | Two independent derivations (different prompts or models) of the reference function, required to agree | Low (correlated errors) | Cheaply | Pre-filter for the audit queue. **Never served** |
| **Declared** | The Planner declares a contract and the Builder writes to it | None | Free | **Never served.** Goes to the audit queue |

**The research bet: textbook worked examples as an oracle.** KSSM textbooks print calculations with inputs and answers. An LLM extracts them; the server checks every number occurs verbatim in the cited passage; the Model must reproduce the printed answers. The *relation* between inputs and answer then comes from the textbook, not from the model. **ASSUMED:** the corpus text is clean enough (4 Chemistry experiment books are scanned images with no text layer, so they are excluded; other extractions were spot-checked clean) and worked examples are dense enough per topic. Measuring that density is a P2 task, free once the corpus is loaded.

**Relation Registry entry types:** `equation` (reference function, units, domain), `law` (sign or monotone trend between Quantities, checkable on a running Model), `process` (ordered stages with conditions, each cited), `fact` (a cited statement). Biology leans on `law`, `process`, `fact`. Physics and Chemistry lean on `equation`. The Registry is finite for the SPM syllabus, so coverage is a number you can report.

### 4.9 Trust ladder and what a student is shown

States: `declared` → `verified` → `cached` → `audited` → `reviewed` → `canonical`, plus `stale`, `evicted`, `rejected`. Closed transition table (v2's `api/labs/lifecycle.py`). Differences from v2:

- v2's `audited` is **machine** re-verification plus an evidence recheck. Keep that meaning.
- v2's `promoted` (three deliveries) is a rule of thumb and says nothing about truth. Replace with `reviewed` (a **human** checked it against the textbook page) and `canonical`.
- Serving policy: `verified` and above. Never `declared`.
- Student-visible provenance, always: "Checked against: Fizik Tingkatan 4, Bab 2, ms. 47 (F = ma). 4 reference cases, 1,681 settings, 3 properties." Plus the honest limit: "Checked against stated cases and properties. Not a proof for every input."

### 4.10 Worked example: Hooke's law (illustrative; confirm the KSSM chapter against the topic taxonomy)

Synapse-V3 already ships a hand-built Hooke's law lab (`backend/services/hookes_law_lab.py`, READ). In v4:

1. **Route**: `physics`, `form 4`, presentation `Stage`, model kind `closed_form`.
2. **Evidence**: retrieve the passage stating F = kx and the elastic limit. Quote verified.
3. **Admit**: `SpringHanger`, `Plot`, `RecordTable`, `HintLadder` are admissible because Quantities of dimensions force, length and stiffness exist.
4. **Design**: Planner picks Relation `hookes_law` and wires `F`, `k`, `x`; ranges; a predict task; three hints.
5. **Verify**: grid over `load` (41 points) by `k` (19 points) = 779 settings, every one run against the reference; properties: extension non-negative, increasing in load, decreasing in `k`.
6. **No Kernel was generated.** The environment is pure data over audited Relations and Parts.
7. **Deliver** as a Peek with an Open action; Stage on tap.

If the student asks "what happens past the elastic limit?", the Relation's domain metadata marks `load` above the limit as outside the model. The Environment says so instead of extrapolating (a "break it" mode, idea B-10).

---

## 5. What to take from Arcana v2

Ranked for the environment direction. Every port starts with a comment naming source repo, path and commit (v2's CLAUDE.md rule 5). Read fully, adapt to v4 interfaces, never paste and patch until it compiles.

| # | Piece (v2 location) | v4 slot | Change needed | Effort |
|---|---|---|---|---|
| 1 | Lifecycle table and store (`api/labs/lifecycle.py`, `store.py`, `audit.py`) | Section 4.9 | Rename states; add `reviewed`, `canonical`; keep "transient failures never evict" | Small |
| 2 | Contract, checker, verifier, mint, runner (`api/labs/contract.py`, `checker.py`, `verifier.py`, `packages/labs-check/*`) | Model verification | **Generalise** from one scalar output to multiple outputs and stepped state (one scalar function per state variable). Keep the allowlist (`allowlist.json`) | Medium |
| 3 | Mutation harness (`api/labs/mutations.py`, `planted*.py`) | Per Part and per model kind | The harness shape ports. The physics mutants are new work | Small to medium |
| 4 | Fixed template host (`web/lib/labFrame.ts`) | The Runtime | Replace the one-slider template with a Part registry host. Keep the hash check, version check, sandbox attribute, CSP | Medium |
| 5 | Catalog `Spec`, `Fences`, `PlacementHint`, `ComposerEvidence` (`api/genui/catalog.py`) | Part records and admission | Preconditions now read Model Quantities and Relations, not retrieval payloads | Medium |
| 6 | `LayoutSpec` v2 and the deterministic layout rules (`api/genui/layout.py`) | Presentations | Panels become presentation regions; phone-first stacking | Medium |
| 7 | Spend ledger and cap at the LLM seam (`api/llm/ledger.py`, `service.py`) | Cost control | Add per-session and per-day student limits | Small |
| 8 | Server-verified verbatim quotes (`api/genui/text.py`, validator grounding rules) | Evidence and claims | None | Small |
| 9 | Saved patterns and reuse (`api/genui/patterns.py`) | Library reuse | Patterns become Environment specs; reuse re-verifies | Small |
| 10 | Mastery rule (`api/learner/mastery.py`, 68 lines) | Device-local learner map | Port to TypeScript; no server store | Small |
| 11 | Cloze quiz from claims (`api/vault/quiz.py`) | Concept checks | Needs a claims pass over the corpus. Estimated at roughly $6 to $7 at v2's measured $0.0033 per passage; not measured on textbook text | Medium |
| 12 | Eval discipline (`eval/stats.py`, `eval/frozen.py`) and subagents `schema-guardian`, `cost-auditor`, `test-runner`, `doc-keeper` | Process | Adapt | Tiny |

**Not taken:** graph and vault retrieval, Orchestrator/Research/Graph/Fact Checker roster, Studio writing and study tools, TracePanel, panes system, Look-style retrieval benchmarks.

**From v1 (Synapse `Synapse/`):** the sourced misconception KB (`backend/app/knowledge/`, with citations: Odom and Barrow, Taber, Clement and Halloun-Hestenes, Driver, Shipstone), the strategy names (contrasting cases, predict-observe-explain, worked-example fading, retrieval practice), and the evaluation plan (10 to 15 students, two-tier diagnostic, pre, post, delayed post).

**From v3 (`Synapse-V3/`):** the 53-topic KSSM taxonomy (`ml/router-distill/kssm_topics.py` v3, each topic citing its source page), the ingested passage index (1,971 passages, 6 subject and form combinations), the distilled router (88.1 percent domain, 70.4 percent artifact type; shadow mode only today), the golden and hostile eval sets (never fully run), the brand and Axi mascot, the router prompt and structured-output lessons (forced tool use after three free-text JSON failures).

---

## 6. Brainstorm: ideas

Fitness is my judgement against one question: **would a Form 4 or 5 student use this weekly, and does it make the verified claim more true?** Not measured.

### 6.1 Core (the design depends on them)

| ID | Idea | Why |
|---|---|---|
| B-1 | **Relation Registry** of audited, cited, reference-backed KSSM Relations | Moves the oracle out of the per-request path |
| B-2 | **Dataflow Model with a unit and dimension checker** | Catches a large error class (mixing N and kg) before any execution |
| B-3 | **Part library by kit, admitted on precondition, gated by planted defects** | The "extensive GenUI components" |
| B-4 | **Data-first Environments**: Kernel glue only when needed | Removes code execution from the common path |
| B-5 | **Part-gap and unregistered-relation backlog** | Library growth is driven by demand, and coverage is a measured number |
| B-6 | **Presentations**: Peek, Stage, Companion, Shelf | Phone-first and reuses OpenAI's restraint rules |

### 6.2 Strong, after the core

| ID | Idea | Why |
|---|---|---|
| B-7 | **Evidence-derived reference cases** (textbook worked examples as oracle) | Independent oracle at scale. Research bet. Section 4.8 |
| B-8 | **Environment as a forwardable single file** (spec plus inlined Runtime, hash-checked) | Keeps v3's best property (self-contained HTML) under the new design. WhatsApp-friendly, offline, school PCs |
| B-9 | **Amali mode**: apparatus bench, hypothesis and variables scaffold, procedure steps, a results table the student fills from their own runs, a report skeleton on export | KSSM experiments follow Problem, Hypothesis, Variables, Procedure, Results. SPM practical tests are reported (PRESS) as scheduled for November 2026 |
| B-10 | **"Break it" mode**: pushing a Quantity past a Relation's stated domain shows the model's limit | Teaches that models have validity ranges. Uses domain metadata already required |
| B-11 | **Misconception-first entry**: a matched v1 misconception selects a predict-observe-explain task whose options resolve by `when` against the live Model | v1's pedagogy on v2's safety |
| B-12 | **Translation as a spec edit**: Bahasa Melayu swaps text fields, Model untouched, verification unchanged | Makes BM a bounded one-time cost per audited Environment |
| B-13 | **Manifest compared with behaviour**: each Environment declares Parts, Kernels and capabilities; the audit checks the declaration against what ran | OpenAI's review pattern, applied locally |
| B-14 | **Exam mirror**: from the live Model state, produce an SPM-style question with a marking scheme and grade the attempt | Gives interaction data a reason to exist for the student |
| B-15 | **Remix as a dataflow edit** ("add air resistance") | Safe because it is a registered Relation, re-verified |

### 6.3 Later or optional

| ID | Idea |
|---|---|
| B-16 | **MCP-Apps-shaped bridge** so Environments can be served inside ChatGPT or Claude (`ui://`, JSON-RPC over `postMessage`). Design the bridge this way from P0 even if nothing is served |
| B-17 | Device-local mastery map with a one-code export (no accounts) |
| B-18 | Chapter pack export for school PCs |
| B-19 | Teacher link preview with the provenance panel |
| B-20 | A "solvability fuzz" on every Part's registration suite, borrowed from Google's extreme-value probing |

### 6.4 Rejected

| Idea | Why |
|---|---|
| ~~Raw generated HTML at runtime in front of students~~ | **Withdrawn by A1.** Kept as a risk: the 39 to 40 percent wrong-physics class exists, so the lane labels and L1, L3, L6 in A1.6 carry the weight |
| GraphRAG over the KSSM corpus | Measured no gain (p = 0.69), and the corpus is small and curated |
| A trained re-ranker | Measured no help (D-37) |
| World-model environments | Unverifiable. Section 3 |
| Pyodide or WebAssembly Python for kernels | Heavy, large attack surface (v2 D-36 rejected it too) |
| An agent per capability | Violates the trust-boundary rule |
| Accounts, payments, teacher dashboards | Still out of scope. Device-local state and forwardable links cover the need |
| Studio writing, flashcards, Cornell notes | Arcana's job |

---

## 7. Proposed hard constraints (for CLAUDE.md)

Mechanism, not preference. A violation is a bug.

1. **No unverified Environment reaches the client.** The deliverable type can only be minted by the verifier. The gate re-derives, re-hashes and re-checks the stored record. The browser re-hashes.
2. **The wire carries data only**, except a Kernel's source, which is inert text until the fixed Runtime places it.
3. **Sandbox**: `allow-scripts` only, never `allow-same-origin`. CSP `default-src 'none'`. No runtime CDN. Libraries from a local vendor directory with an allowlist.
4. **Ground before generating.** No Environment without a stored KSSM passage that states what it models. Otherwise `empty` with a reason and a text answer.
5. **Only the Composer chooses Parts and layout**, by deterministic admission on evidence. Invalid blocks are dropped, never repaired.
6. **Parts and Relations join on evidence.** A Part needs a written precondition, fences and a registration suite that refuses every planted defect. A Relation needs a textbook citation, a reference implementation and properties.
7. ~~Raw generated code never reaches a student.~~ **Superseded by A1.6:** raw generated HTML may reach a student only after the full verification of its lane, carrying that lane's honest trust label. Free-lane output is never `canonical` without human review.
8. **Declared contracts are never served.** Only registered or evidence-derived references qualify (section 4.8).
9. **Spend is capped** at the LLM seam, and public traffic is limited per session. Every paid call goes through the seam and the ledger. Fakes by default.
10. **Evaluation protocol is fixed before runs.** Model-judged scores are never the primary metric. Golden and hostile sets are hash-pinned.
11. **Accessible and phone-first by construction.** Every Part exposes a text equivalent; 360 px, 44 px targets, reduced motion; checked statically and in a real browser.
12. **Honest provenance is always visible**: the citation, what was checked, and its limits.
13. **Public-repo hygiene.** No secrets, no personal data, no textbook PDFs, no Hackathon admin material. Ports carry provenance comments.

Process rules inherited from the doc system (`/newproject`): changelog every session, plan before build, ADRs for decisions, never build the second of anything until the first is green end to end.

---

## 8. Modules and build order

No dates. Each phase has a definition of done and does not start until the previous one is met.

| Phase | Scope | Definition of done |
|---|---|---|
| **P0** Walking skeleton and census | Repo, schema codegen, fakes by default, ledger. One closed-form Environment spec rendered by a fixed Runtime through mint and gate. **Coverage census**: for each of the 53 topics, which model kinds and Parts it would need (free, no model call) | One Environment goes question to render on fakes. A census table exists with counts per kind |
| **P1** Model core | Dataflow plus units, Registry with the first ~15 Relations of one chapter, verifier generalised to closed-form and stepped, mutation suite v1, Runtime v1 with core Parts, kernel isolation spike (QuickJS in WASM versus locked container) | All planted defects refused by the named stage; a stepped Environment verified exhaustively; isolation choice recorded |
| **P2** Evidence | Ingest the curated corpus (manifest, no PDFs in repo), hybrid retrieval over passages, evidence gate, verbatim quotes, citation chips, relation drafting tool, **worked-example density measurement** | Every claim in a rendered Environment carries a verified quote; worked-example density reported per topic |
| **P3** Planner and first vertical | Router (local plus LLM fallback), Planner, admission, honest degrade, one Physics chapter end to end, first paid run with confirmed amount | Golden set for the vertical passes; cost and latency per Environment measured |
| **P4** Kits | Mechanics complete, then Chemistry, then Biology (process, stochastic). Each kit through registration suites, a11y, phone visual checks | Per-kit coverage number reported against the census |
| **P5** Library and lifecycle | Store, cache path with re-verify, audit, human review queue, syllabus Shelf, metrics | A covered topic opens under one second with no model call; a flag evicts |
| **P6** Pedagogy | Predict tasks with `when`, misconception KB port, hint ladder, concept checks, device-local mastery, Amali mode, exam mirror | Three flagship misconceptions run end to end |
| **P7** Reach | Bahasa Melayu for reviewed Environments, offline single file, share links, MCP-Apps-shaped bridge, public deploy with isolation and rate limits | A student on a phone can open a shared link offline |
| **P8** Evidence and study | Learner study per v1's plan, paper-ready evaluations | A normalised-gain result, whatever it shows |

---

## 9. Open decisions (the interview)

| # | Decision | Recommendation | Why |
|---|---|---|---|
| Q1 | Adopt "Environment" as the term and the five-part definition | Yes | Section 1 |
| Q2 | Runtime raw HTML lane | **DECIDED by the owner (A1): raw HTML stays primary**, over a Kit, in three lanes | Adaptivity and generativity; v3 behaviour is preserved, not regressed |
| Q3 | Stack shape | **DECIDED by the agent, as the owner asked (A1.8): Python API (FastAPI, uv) plus Next.js web (pnpm) plus TypeScript schema with codegen to Pydantic plus a JS Kit package**, the Arcana v2 shape | The verifier, lifecycle and test corpus are already proven in Python; the ML and ingestion assets are Python. Alternative: TypeScript end to end so the verifier and the browser share one evaluator (a real correctness benefit, at the cost of rewriting the ports). Revisit after the P1 isolation spike |
| Q4 | First vertical | **DECIDED by the owner: the P0 census decides** | Measured counts, not my estimate |
| Q5 | Kernel isolation for public deploy | Decide in the P1 spike: QuickJS (WASM, no Node) versus a locked container | `node:vm` is not isolation (v2's own docs) |
| Q6 | Git | **DECIDED (owner: "either one or two"): init here and add `Synapse-V4/` (the on-disk case) to the monorepo's ignore list** | The folder will be opened on its own; an ignore line prevents an embedded-repo warning in the monorepo |
| Q7 | Corpus handling | PDFs and extracted passages gitignored; a manifest and an ingestion script in the repo | Copyright is the Ministry's. Short quotes with citations only. **Unconfirmed legal position, confirm before any public deploy** |
| Q8 | Languages | English first, **string tables from P0**, Bahasa Melayu in P7 for reviewed Environments only | Translation is a spec edit (B-12) |
| Q9 | Name | Keep "Synapse v4" for now; decide before a public URL | Collision with a published 2026 SYNAPSE tutor paper |
| Q10 | Providers and budget | Anthropic primary, tiered models, OpenRouter fallback, **fakes by default**, monthly cap in settings | v2's seam is proven |
| Q11 | Users | Public students, no accounts, device-local state; teachers by forwardable link | Stimuli S1 to S4, S7 from the v3 idea-darwin work |
| Q12 | Human review capacity | Solo reviewer. Report minutes per Relation in P1 and size the Registry from that | The audit-time bottleneck is the real constraint |

---

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Composition cannot express enough of the syllabus | Product ceiling | Census in P0 and per-kit coverage numbers. Part gaps and unregistered relations are logged data |
| Registry authoring is slow | Coverage stalls | LLM drafts from passages, human reviews against the page; measure minutes per Relation before scaling |
| Part library is the long pole | Months of UI work | Interaction-pattern Parts, kit gating, a gallery that doubles as the audit and regression surface |
| The oracle is weaker than it looks (correlated errors) | A verified-but-wrong Environment | Section 4.8 ladder; never serve `declared`; human `reviewed` state; mutation testing of the verifier on physics bugs |
| Stochastic and process models verify weakly | Overclaim | Label the strength in the UI; do not call them proven |
| Public exposure | Cost and abuse | Per-session limits, cached-first policy, spend cap, isolation before deploy |
| Textbook licensing | Legal | Q7. Quote briefly with citation; do not redistribute |
| Commoditisation by OpenAI and Google | Relevance | Differentiate on KSSM exactness, BM, practical and exam modes, offline, inspectable verification |
| "Environment" and "Synapse" naming collisions | Confusion | Section 1.5 and Q9 |
| Over-scoping into Arcana's territory | Drift | Section 6.4 rejected list and constraint 13 |

---

## 11. Sources and provenance

**Arcana v2** (own repo, public, `Azimlearning/Arcana-v2`), commit `21c6dcf54e8c38b0e7e4556e478acd4d42e82bd7` (2026-10-16, 136 commits, clean tree): `CLAUDE.md`; `refdocs/STATUS.md`; `refdocs/changelog/DECISIONS.md` (D-27 to D-44); `refdocs/plans/2026-10-08-p4-verifiedlab.md`; `refdocs/evidence/20261015-lab-live-generator.md`; `refdocs/evidence/20261008-p4-lab-mutation-suite.md`; `refdocs/guides/catalog.md`; `api/labs/{contract,verifier,lifecycle,live_generator}.py`; `api/genui/{catalog,layout}.py`; `web/lib/labFrame.ts`; `packages/labs-check/allowlist.json`.

**Genui monorepo** (own repo, public, `Azimlearning/GenUI-Education`), as read on 2026-10-16: `Synapse/{CLAUDE,REPORT,project-state,decisions}.md` (v1); `synapse-v2/README.md`; `Synapse-V3/{README,HANDOFF}.md`; `Synapse-V3/docs/{PLANNING,EVALS,UX_IMPROVEMENT_PLAN,ENHANCED_VERSION_PLAN}.md`; `Synapse-V3/docs/idea-darwin/{ideas,island,round-01,stimuli}.md`; `Synapse-V3/ml/{IMPLEMENTATION_PLAN.md,rag/README.md}`; `Synapse-V3/backend/services/{builtin_labs,local_router}.py`; `Synapse-V3/backend/graph/nodes/router.py`; `research/generative-ui-research-2026-07-06.md`; `MCAIT/Paper/*` (private nested repo).

**External (accessed 2026-10-16):**
- OpenAI, [UI guidelines](https://developers.openai.com/apps-sdk/concepts/ui-guidelines), [UX principles](https://developers.openai.com/apps-sdk/concepts/ux-principles), [Add UI to your MCP server](https://developers.openai.com/apps-sdk/plan/components), [ChatKit widgets](https://developers.openai.com/api/docs/guides/chatkit-widgets)
- OpenAI, [New ways to learn math and science in ChatGPT](https://openai.com/index/new-ways-to-learn-math-and-science-in-chatgpt/) (403 on fetch; figures from [Campus Technology](https://campustechnology.com/articles/2026/03/10/openai-adds-interactive-math-and-science-learning-tools-to-chatgpt.aspx), [Engadget](https://www.engadget.com/ai/chatgpt-will-now-generate-interactive-visuals-to-help-you-with-math-and-science-concepts-170000520.html), [TechCrunch](https://www.techcrunch.com/2026/03/10/chatgpt-can-now-create-interactive-visuals-to-help-you-understand-math-and-science-concepts))
- Google Research, [The future of practice](https://research.google/blog/the-future-of-practice-enabling-teachers-to-create-learning-interactives-with-generative-ui/), 17 Sep 2026; [arXiv 2609.20738](https://arxiv.org/abs/2609.20738) (abstract only)
- [MCP Apps overview](https://modelcontextprotocol.io/extensions/apps/overview) and [ext-apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- Vercel json-render: [InfoQ](https://www.infoq.com/news/2026/03/vercel-json-render/), [LogRocket](https://blog.logrocket.com/vercel-json-render-dynamic-ui/) (secondary; official README not opened)
- [PDE-grounded intent verification, arXiv 2605.09360](https://arxiv.org/abs/2605.09360)
- [WorldRoamBench, arXiv 2606.31672](https://arxiv.org/pdf/2606.31672); [Project Genie coverage](https://9to5google.com/2026/01/29/google-project-genie/)
- [MAIC-UI, arXiv 2604.25806](https://arxiv.org/abs/2604.25806); [The Missing Layer, arXiv 2606.15902](https://arxiv.org/abs/2606.15902)

**Not read:** OpenAI's own interactive-learning announcement (403), json-render's repository, the full text of arXiv 2609.20738, any KSSM textbook in this session (taxonomy and passage counts are taken from the v3 ML docs).
