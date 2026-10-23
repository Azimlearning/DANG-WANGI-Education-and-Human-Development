# Synapse v4: Product Requirements Document (PRD)

> Synapse v4 gives a Malaysian Form 4 or 5 KSSM student an **environment** for a science question: a bounded, interactive world, generated as raw HTML/JS over a vetted library of hundreds of micro-components (a Kit), in which a verified model of the science responds, with the textbook evidence and an honest trust label beside it. Generation is made faster, cheaper and more reliable by prepared prompt packs, the Kit, a growing library of verified environments, and a set of accelerator functions. It is the fourth build in a lineage (v1 component selection, v2 formula DSL, v3 raw-HTML generation behind a delivery gate) and borrows its lifecycle, planted-defect discipline and cost control from Arcana v2.

- **Owner:** Azim (Fakhrul Azim), sole author
- **Users:** Malaysian KSSM Form 4 and Form 5 students (Physics, Chemistry, Biology), phone-first, no accounts. Operated by one person for now (D-11)
- **Status:** Scaffolded 2026-10-16, pre-implementation
- **Last updated:** 2026-10-16
- **Source of record:** [synapse-v4-sources.md](synapse-v4-sources.md)
- **Founding context:** [brainstorm-2026-10-16.md](brainstorm-2026-10-16.md) (historical; its Amendment A1 records the interview that changed the central choice)

---

## 1. Context & Hard Constraints

Confirmed from the owner's messages and interview (2026-10-16) unless marked otherwise.

| Constraint | Value | Consequence |
|---|---|---|
| Purpose | An extensive GenUI component set that generates learning "environments" | The Kit is the product's main body of work, not a side library (D-03) |
| Term | "Environment", not "lab" | One artifact word covering experiments, process explorers, data investigations, practical benches and exam rooms (D-01) |
| Generation | Raw HTML/JS stays primary, as in v3 | Adaptive and generative; correctness must be enforced around it, not by restricting it (D-02) |
| Deadline | None, open-ended | Sequence by dependency and evidence, not by date |
| Cost model | Pay-per-use Anthropic API. Fakes by default. The owner confirms every paid run. Monthly cap | A fake LLM and a spend seam exist before any live call (D-08) |
| Exposure | Designed for students with no accounts. Operated as a single-operator tool: no auth, no rate limit | Public exposure is blocked until a deploy gate is met (D-11). Student state is device-local |
| Repo | Lives in the Genui monorepo now, becomes its own GitHub repo, opened on its own | Docs are self-contained. Ports carry provenance. The folder is git-ignored by the monorepo (D-10) |
| Stack | Delegated to the agent, "whichever is faster, especially for the raw html components" | Python API + Next.js + schema + JS Kit (D-05) |
| First vertical | Decided by a P0 coverage census | No subject is assumed before measurement (D-09) |
| Dev machine | Windows, no Docker, no Postgres, about 17 GB free on a 94 percent full disk (observed 2026-10-16) | SQLite locally; avoid large installs; Playwright browsers are a known cost |
| Privacy | No student personal data stored server-side | Progress and saved environments live on the device |
| Legal | KSSM textbooks are Ministry of Education works | Corpus stays out of the repo; short cited quotes only; position unconfirmed (D-14, A-8) |

---

## 2. Product Principles

1. **Adaptive and generative, but bounded.** The model writes the document. What it may call, and where numbers may come from, is bounded by the Kit and checked.
2. **Truth lives in audited micro-models.** Science is written and reviewed once, cited to a textbook page, and reused hundreds of times. The generator composes it; it does not re-derive it.
3. **Reuse before generate.** The cheapest, fastest and safest environment is one that already exists and was re-verified.
4. **Verify what can be reached.** A control that a student can move is tested at its grid and at its extremes, not sampled.
5. **Honest labels.** What was checked, against what, and what was not, is visible to the student and the teacher.
6. **Phone first.** The 360 px lab is the product. Desktop is the widened variant.
7. **Cheap by construction.** Output tokens are the main cost; the Kit, prompt packs and accelerators exist to shrink them.
8. **The Kit grows from measured gaps.** Free-lane generations and part gaps are data that order the work.

---

## 3. Architecture

### 3.1 Three lanes

The lane is decided by what verification the output survives, not by what the generator intended. A Compose attempt that fails the Kit-provenance check is relabelled `model-checked` or retried.

| Lane | What the LLM writes | Cost and time | Trust label | When |
|---|---|---|---|---|
| **Instantiate** | Nothing, or a small fill (labels, ranges) | About zero to one small call; seconds | `kit-verified`, then `reviewed` or `canonical` once audited | A library hit or a stored composition covers the pattern |
| **Compose** (primary) | Raw HTML/JS that calls the Kit: layout, glue, custom scene pieces | One generator call with a short output | `kit-verified` when every displayed number comes from a Kit science micro-model and the assembly checks pass | Default for a new question |
| **Free** | A whole raw HTML document, no Kit, v3 style | v3-like: tens of seconds, about $0.19 (measured in v3) | `model-checked`: an honest, weaker label. Never `canonical` without human review. Feeds the Kit gap backlog | The Kit cannot express it |

### 3.2 The Mark 3 pipeline

Mark 1 is v3's single-shot generation with an LLM verifier. Mark 2 is Arcana v2's template, fences, checking, save, reuse pipeline with its lifecycle and compiled-vault direction. Mark 3 is Mark 1's raw-HTML generation restructured around a Kit, prompt packs and accelerators, keeping Mark 2's lifecycle, planted-defect discipline and compounding library (D-04).

| # | Stage | Who | On failure |
|---|---|---|---|
| 1 | **Route**: topic ids, pattern, `text_only` | Local classifier, LLM fallback below a confidence threshold | Non-science or out of syllabus exits to text |
| 2 | **Retrieve and look up**: textbook passages; library lookup by canonical key | Deterministic | A library hit goes to Instantiate |
| 3 | **Plan**: quantities, relations by id, tasks, study note, steps | LLM, forced tool use | Schema failure retries once, then degrades |
| 4 | **Assemble the prompt**: core, pattern pack, kit pack, exemplar, plan | Deterministic | n/a |
| 5 | **Generate** (Compose or Free), streamed | LLM | Counts as an attempt |
| 6 | **L0 post-process**: scan, CSP, size | Deterministic | Refuse; retry with the named issue |
| 7 | **L1 Kit provenance** | Deterministic | Relabel Free or retry |
| 8 | **L2 render and fuzz** in headless Chromium | Deterministic | Refuse; retry |
| 9 | **L3 numeric cross-check** against the micro-model's own reference | Deterministic | Relabel Free or retry |
| 10 | **L4 LLM verifier** | LLM, forced tool use, small | Retry with issues, at most 2 |
| 11 | **L5 mint, store, gate** | Deterministic | Never serve on a failed gate |
| 12 | **Deliver**: SSE blocks, client re-hash, sandboxed iframe | Fixed code | Honest degrade card |

Retries use the verifier's issues. A branch degrades early instead of starting a revision without enough time or budget left (v3 finding).

**Layers and skeletons (D-23).** The table above is the order of work; the design that makes it cheap and reliable is in `refdocs/plans/2026-10-16-p3-mark3-pipeline.md`. In short: the model's main output is a validated **Plan** (data); **plan checks** run before any HTML exists; a deterministic **assembler** builds the page from a per-pattern **skeleton**; the model writes only short typed **slot fills** for parts the skeleton cannot express; a **fail-check registry** names every refusal; and a **degrade ladder** (Instantiate-by-plan, Compose with fills, Free labelled, text) means no blank screen. The student sees a **loading skeleton** (the Peek shell from the Plan) before verification finishes. The research behind it: `refdocs/evidence/2026-10-16-chatgpt-ui-research.md`.

### 3.3 Verification layers and what they guarantee

| Layer | What | Lane | Status |
|---|---|---|---|
| L0 | Forbidden-API scan, CSP injection, size cap, single document | all | Exists in v3 (to port) |
| L1 | Kit provenance: pinned bundles only; `readout` arguments are observables; control-derived arithmetic outside Kit calls is counted; numeric text in readout regions probed against observables | Compose | New |
| L2 | Render and fuzz: ready within 5 s, controls wired, no uncaught error, reset works; plus grid and extreme values | all | v3 harness, extended |
| L3 | Numeric cross-check: harness drives controls to grid and extreme points and compares displayed values with the micro-model's own reference, evaluated independently | Compose | New |
| L4 | LLM verifier: pedagogy, labels against units, expected behaviours, spot checks | all; the only science check in Free | Exists in v3 |
| L5 | Mint and gate: only the verifier mints; the gate re-hashes and re-checks | all | Exists in v3 and Arcana v2 |
| L6 | Planted-physics-bug suite run against the verifier, producing a detection rate | process | New |

**Guaranteed in Compose (L0 to L5), subject to the limits in D-24:** the numbers the Environment computes come from audited micro-models, the numbers in its sentences match a control value or a model setting, and the assembly works across the tested grid; the Kit also watches itself in the student's browser and the host closes an Environment that changes what the Kit drew. **Not guaranteed:** that the scene tells the truth (a correct number beside a misleading picture), which only L4 and review catch. **Free:** model-checked only, the strength of v3, unmeasured, labelled so.

### 3.4 The Kit

A micro-component is the smallest reusable, versioned unit with an id, a signature, a written precondition, an accessibility fence, tests, and documentation short enough to put in a prompt.

| Kind | Examples | Carries truth | Registration requires |
|---|---|---|---|
| ui | slider with live value, readout tile, reset, steps strip, study-note card, hint ladder | no | a11y suite, 360 px layout test |
| scene | axes, vector arrow, beaker, burette, flask, spring, lens, ray, membrane, particle field | no | render test, no overflow at 360 px |
| interaction | pointer-events drag with drop target, swirl detector, valve knob, eye-level parallax | no | gesture test in a real browser, touch and keyboard path |
| **science** | `mechanics.projectile`, `mechanics.hookes`, `gas.boyle`, `chem.titration_curve`, `bio.osmosis_flux`, `genetics.punnett` | **yes** | textbook citation, units and domain, independent hand-written reference, properties, planted-defect suite |
| pedagogy | predict card, concept check, misconception probe, worked solution, results table | no | behaviour test; `when` predicates resolve against live observables |
| bridge | ready, event, error, model-visible summary | no | protocol test |

**Generation micro-components (D-23).** Components that remove work from the model, each built to the rules above: `experiment` (the Amali card), `resultsTable` and `record`, `graph`, `reset`, `stepper`, `predictCard`, `hintLadder`, `conceptCheck`, `workedSolution`, scenes bound to observables (`springScene`, `circuitScene`, `tankScene`, `vectorArrow`, `axes`), and inputs (`select`, `toggle`, `numberInput`, `dragDrop`). A scene draws a quantity and never prints one. Every manifest entry also carries a `useWhen` sentence and described arguments, because the kit pack is chosen by retrieval over them, the way ChatGPT discovers tools by their descriptions.

"Hundreds" is the owner's target and a direction, not a count. The size guess in A-2 is replaced by the P0 census.

The Kit is semver-versioned. Every stored environment records the Kit version it was verified against, so a Kit bump marks it stale until re-verified. The manifest (ids, signatures, preconditions, citations, one-line docs) is generated from the Kit and is the only thing the API reads.

### 3.5 Prompt packs

| Segment | Content | Chosen by | Cache |
|---|---|---|---|
| core | goal, hard rules, bridge contract, accessibility, size cap | fixed | stable prefix, cached |
| pattern pack | rules and one exemplar for: simulation, virtual experiment, explorable diagram, data viz, drag-drop, process stepper, exam practice, Amali bench | router output | cached per pattern |
| kit pack | signatures and one-line docs of the 8 to 15 relevant micro-components | Kit retrieval | per request, small |
| exemplar | one or two nearest golden compositions | nearest topic and pattern | per request |
| plan | the structured plan | planner | per request |

### 3.6 Accelerators

Library lookup; template instantiate; edit-not-regenerate (diff against a stored script); Kit retrieval; model tiering; prompt caching; skeleton first; early gates; deterministic repair; per-pattern output budget; overnight batch fill; question canonicalisation; per-request budget with degrade. The full table with what each saves is in `brainstorm-2026-10-16.md` A1.5.

### 3.7 Presentations (adopted from OpenAI's display modes, A-7)

| Presentation | Use | Rules |
|---|---|---|
| Peek | Inline card in the conversation: one live readout, at most one control, one Open action | At most two actions, no tabs, no nested scrolling |
| Stage | Full screen; the environment is the answer; the composer stays overlaid | Phone-first |
| Companion | Small persistent view while follow-ups are asked | Closes when the task ends |
| Shelf | Carousel of library environments for a topic or chapter | 3 to 8 items, one action each |

### 3.8 Trust ladder

`verified`, `cached`, `audited` (machine re-verification plus an evidence recheck), `reviewed` (a human checked it against the textbook page), `canonical`; plus `stale`, `evicted`, `rejected`. A closed transition table ported from Arcana v2's `api/labs/lifecycle.py`. A transient failure never evicts. Reuse re-verifies before serving.

---

### 3.9 Components

| Component | Responsibility | Surface |
|---|---|---|
| Wire schema | Typed blocks, SSE events, error envelope; TypeScript to Pydantic | `packages/schema` |
| Kit | Micro-components, bundles, manifest | `packages/kit` |
| LLM seam | Providers, tiers, spend ledger, cap, fakes | `api/llm` |
| Evidence | Corpus manifest, ingestion, retrieval, verbatim quotes, citations | `api/evidence` |
| Router | Local classifier plus LLM fallback, canonicalisation | `api/routing` |
| Models | Trained local models (multi-head router, misconception matcher), model cards, retraining | `api/models`, `eval/models` |
| Experiments | The experiment catalogue: one record per KSSM practical, Amali fields, topic and Environment mapping | `api/experiments`, `data/experiments` |
| Pipeline | Plan model and checks, skeletons and the assembler, slot fills, prompt assembly, the fail-check registry, orchestration, retries and the degrade ladder | `api/pipeline`, `api/prompts` |
| Verification | L0 to L5, mint, gate, mutation suites | `api/verify` |
| Library | Store, lifecycle, audit, review queue | `api/library` |
| Pedagogy | Tasks, misconceptions, hints, concept checks | Kit plus `api/pedagogy` |
| Web shell | Chat, presentations, sandbox host, hash check | `web` |
| Eval | Golden, hostile, planted-bug, census, cost | `eval` |

### 3.10 Data & state

| Store | Contents | Where |
|---|---|---|
| Environments | id, lane, label, state, kit version, prompt-pack version, HTML and its SHA-256, plan, citations, timestamps | SQLite (local), a managed database at deploy |
| Spend ledger | every paid call, tokens, cost, purpose | SQLite file, gitignored |
| Traces | per-stage input, output, model, tokens, latency | SQLite |
| Flags and ratings | wrong-science flags, ratings | SQLite |
| Student state | progress, saved environments, mastery | the device only (D-11) |
| Corpus | textbook passages and index | local, gitignored (D-14) |

---

## 4. Modules / Feature Areas

| Module | What it owns | Phase |
|---|---|---|
| schema | wire types, codegen, drift check | P0 |
| kit | micro-components, manifest, gallery | P0 to P4 |
| verify | L0 to L6, mint, gate | P0 to P1 |
| evidence | ingestion, retrieval, quotes, citations | P2 |
| models | trained local models, model cards, retraining | P1b |
| experiments | the experiment catalogue, validator, ingestion tooling | P2 to P4 |
| pipeline | router, planner, prompt packs, generation | P3 |
| library | store, lifecycle, review, shelf | P5 |
| pedagogy | predict, misconceptions, hints, checks, mastery, Amali, exam mirror | P6 |
| reach | Bahasa Melayu, offline file, share links, deploy gate | P7 |
| eval | golden, hostile, planted bugs, census, study | P0 to P8 |

---

## 5. Non-Goals

Explicitly out of scope. Revisit only by adding an ADR that says why.

- Accounts, authentication, payments, teacher dashboards (dormant, not forbidden; the owner chose single-operator, no auth, ASSUMED permanent for v1). A "Present" mode that projects one Environment to a class is a presentation of Stage, not a dashboard, and is in scope (D-39)
- Graph retrieval or GraphRAG (D-12)
- A workspace over user-uploaded documents, writing or study-tool suites (Arcana's job)
- World-model or video-style generated environments (unverifiable)
- Pyodide or WebAssembly Python in the browser
- Native mobile apps and collaborative sessions
- Serving the product on a public URL before the deploy gate is met (D-11)

---

## 6. Build Roadmap

No dates. A phase starts when the previous one's exit criteria are observed.

| Phase | Scope | Exit criteria |
|---|---|---|
| P0 Walking skeleton and census | Workspace, schema codegen, fake LLM and ledger, Kit v0, one hand-written Environment, L0 and render harness, mint and gate, web shell, coverage census of the 53 topics | One Environment goes from question to a sandboxed render on fakes; a planted defect is refused at its named layer; a census table of 53 rows exists |
| P1 Kit core and verification | Observables and the core micro-components, 3 science micro-models with references (Hooke's law, Ohm's law, liquid pressure), manifest, L1 provenance, L2 with grid, extremes and a reachable goal state, L3 cross-check, planted-defect suites, L6 baseline, hostile set port, isolation spike, label ladder (D-21), the "What was checked" data | Planted defects refused at the named layer; verifier detection rate recorded; isolation choice recorded |
| P1b Models track | Multi-head router trained on the v3 dataset, baselines, confidence gate, model card, inference module; misconception matcher as retrieval | Held-out metrics against baselines recorded in a model card; the router beats both baselines or is not used |
| P2 Evidence | Corpus manifest and ingestion, retrieval, evidence gate, verbatim quotes, citation chips, relation drafting tool, worked-example density measurement; the experiment catalogue schema, validator and ingestion tooling | Every claim shown carries a verified quote; density reported per topic; the catalogue validates. Real-corpus steps run locally |
| P3 Mark 3 pipeline and first vertical | The layered pipeline (D-23): router, Plan and plan checks, skeletons and the assembler, slot fills, prompt packs, fail-check registry, Kit retrieval by `useWhen`, loading skeleton, Compose and Free lanes, lane labelling, accelerators 1 to 4, 6, 8, 10, first paid run (confirmed) | Golden set for the vertical passes; cost and latency per environment measured against the A-4 hypothesis |
| P4 Kit expansion and Environment authoring | Mechanics, then Chemistry, then Biology kits; gap backlog; gallery; a11y and phone checks; author the Environments for the catalogue | Per-kit coverage reported against the census; at least 3 verified Environments per subject (D-19) |
| P5 Library and lifecycle | Store, re-verify on reuse, audit, review queue with flag-to-regression-eval, syllabus Shelf, edit-not-regenerate (remix is its acceptance test), overnight fill | A covered topic opens in under one second with no model call; a flag evicts and writes a regression eval |
| P6 Pedagogy | Predict tasks, misconception port, hint ladder, challenge levels, concept checks, tutor loop from bridge events, device-local mastery and learner map with an export code, Amali mode, exam mirror | Three flagship misconceptions run end to end |
| P7 Reach and deploy gate | Bahasa Melayu for reviewed environments, offline single file and chapter packs for school PCs, share links, MCP-Apps-shaped bridge, cost dashboard, limits, isolation, store attestation (A-19), deploy gate recorded | A student can open a shared link offline; the gate checklist is complete |
| P8 Evidence and study | Learner study, paper-ready evaluations | A normalised-gain result, whatever it shows |

### 6.1 End-state targets and headline metrics (D-19)

The build is finished when all of these are true. Each names the phase that produces it. None exists yet.

| Target or metric | Value to report | Phase |
|---|---|---|
| Verified Environments | At least 3 each for Physics, Chemistry and Biology (9 in all), each tied to a catalogued experiment or topic, each with its honest label and `checked` record | P4 |
| Experiment catalogue | One validated record per KSSM practical experiment, with the share that has an Environment | P2, P4 |
| Syllabus coverage | Environments in the library divided by the 53 topics, per subject | P5 |
| Verifier detection rate | Planted physics bugs caught, per layer and overall (L6) | P1, repeated each phase |
| Hostile block rate | Must be 100 percent, at two layers | P1, P3 |
| Golden pass rate | pass@2 on a KSSM-mapped golden set for the vertical | P3 |
| Time to a covered Environment | p50, with no model call | P5 |
| Cost | Per Environment generated, and per student per week | P3, P7 |
| Router quality | Held-out accuracy and coverage at the chosen confidence threshold, against baselines | P1b |
| Learning gain | Normalised gain, whatever it shows | P8 |

---

## 7. Decision Log

Canonical one-line list. Load-bearing entries are expanded as ADRs in `changelog/DECISIONS.md` under the same id.

| # | Decision | Why |
|---|---|---|
| D-01 | "Environment" is the artifact term, with the five-part definition (model, scene, instruments, task and scaffolds, evidence) | Owner: environment is better than lab; covers more than experiments |
| D-02 | Raw HTML/JS stays the primary generated artifact, in three lanes (Instantiate, Compose, Free) | Owner: more adaptive and generative; v3 behaviour preserved |
| D-03 | A Kit of hundreds of micro-components, including audited science micro-models, is an allowed building block | Owner: topics and fields are known; resolves v3 rule 4 |
| D-04 | Mark 3 pipeline: prepared prompt packs, the Kit and accelerator functions, on top of Mark 2's lifecycle | Owner: faster, cheaper, more efficient generation |
| D-05 | Python API (FastAPI, uv) + Next.js web (pnpm) + `packages/schema` + `packages/kit` | Agent's call as delegated: reuses the tested raw-HTML pipeline and Arcana v2 lifecycle |
| D-06 | Sandbox and delivery gate carried over: `allow-scripts` only, CSP names the origin, same-origin libraries, verifier-only mint, gate re-hashes | Hard rules from v3 and Arcana v2, proven in both |
| D-07 | The Free lane is served with an honest label, queued for review, never `canonical` unreviewed | Owner |
| D-08 | Fakes by default; the owner confirms each paid run; a monthly cap at the LLM seam | Owner |
| D-09 | The first vertical is decided by the P0 census | Owner (resolved provisionally by D-18) |
| D-10 | `git init` inside this folder and ignore it in the monorepo; docs are self-contained | Owner: either option; later only this folder is opened |
| D-11 | No accounts; single operator, no auth, no rate limit; public exposure blocked until a deploy gate is met | Owner, with the agent's resolution of "public students" versus "single user" |
| D-12 | No graph retrieval; BM25 or TF-IDF first, dense embeddings only if measured to help | Arcana v2 measured no gain (p = 0.69) |
| D-13 | Process: this doc system, subagents `doc-keeper`, `cost-auditor`, `kit-guardian`, and the secret-guard hook only | Owner chose the subagents; other hooks wait until a rule is broken |
| D-14 | The corpus is local and gitignored; a manifest and ingestion script are committed | Copyright is the Ministry's; legal position unconfirmed |
| D-15 | Live mode needs only an Anthropic key and a cap; OpenRouter is optional; no live provider exists until P3 | CLAUDE.md lists OpenRouter as optional; a live path is not built before the owner confirms paid runs |
| D-16 | The Kit semver is tied to its bundle bytes by `kit-lock.json`; stored Environments carry the bundle hash | Hard constraint 6; found by kit-guardian S2 |
| D-17 | The CSP must be the first element; ambiguous markup is refused; verification presses real input and treats navigation as a refusal | kit-guardian B1 and B2, both reproduced |
| D-18 | The first vertical is Physics Form 5 (force and elasticity, forces and pressure, electricity); resolves D-09 provisionally | Owner delegated the choice; Hooke's law already exists |
| D-19 | End state: at least 9 verified Environments, 3 per subject, each tied to a catalogued KSSM experiment or topic; an experiment catalogue module | Owner |
| D-20 | A models track: small trained local models (multi-head router; misconception matcher as retrieval), measured against baselines before they may gate anything | Owner asked for trained-model components; IDEA-0003 |
| D-21 | `model-checked` = passed the deterministic layers with no verified source; `kit-verified` also needs a verified citation; `dev-fixture` is removed in P1 | Hard constraint 4 |
| D-22 | Cloud-first, local last; limits go in the Deferred to local register | Owner |
| D-23 | Mark 3 is layered and skeleton-first: plan as data, deterministic assembly from a per-pattern skeleton, model fills only typed slots; a fail-check registry; a loading skeleton; Kit `useWhen` retrieval | Owner asked for layers, skeletons, prompt templates, fail checks and generation micro-components; ChatGPT apps research |
| D-24 | The page's numbers are protected in four places (lockdown, ownership, verifier, runtime self-check); none is a proof alone | kit-guardian P1 round 1 |
| D-25 | `kit-verified` only when the corpus re-proves every citation (mint and gate); never in the Free lane | Hard constraint 4 |
| D-26 | Lane names say what was done for this question: Compose for pages planned and assembled for it, Instantiate for stored pages reused, Free not built; fills dropped on a verify failure before words-only | kit-guardian P3 B1 |
| D-27 | The library is a canonical-question cache; every hit goes through the gate again; withdraw, restore, flag, stale by Kit hash | Hard constraint 1 |
| D-28 | A local `none` topic is never trusted; it goes to the LLM fallback | Measured: 7 of 24 golden questions wrongly `none` |
| D-29 | Kit 0.1.0 stays unreleased and is relocked until the deploy gate; Kit files are served `no-cache` | D-16 |
| D-30 | Plan checks know cross-quantity rules (PLAN-015) and topic fit (PLAN-016); prompt packs keep per-request text below the divider | kit-guardian P3 S1, S5, S6 |
| D-31 | Stored Environments are HMAC-signed with a key outside the data directory; the gate refuses unsigned or altered rows when a key is set | A-19, hard constraint 1 |
| D-32 | The offline single-file export carries the Kit and both hashes, re-checks them before running, and keeps `sandbox="allow-scripts"` only | P7 reach |
| D-33 | Progress is device-local: the first concept-check answer per Environment, shown in words, with an export code and no account | P6 |
| D-34 | Live mode builds the Anthropic provider; a billed reply we reject is booked at its real usage; tests may only touch this machine | Found when wiring the provider (ledger under-count; a test reached the network) |
| D-35 | A unit conversion must start from the unit its source is in; sentence numbers include `.99` and `5e1` | kit-guardian P1 round 3 |
| D-36 | Citations are pointers in the repo and quotations beside the local corpus; the Plan's citations decide the label | Hard constraint 4 and rule 13 |
| D-37 | The audit refuses every CSS route to a number with no text node, shown exploitable or not | kit-guardian round 3 leads, closed by hardening |
| D-38 | The web UI takes Synapse V3's design language; four V3 behaviours are not ported (code streaming, draft view, post-hash fitting, raw saved HTML) | Owner: UI builds on V3; hard constraints 1 and 3 |
| D-39 | Scope is the PRD end state plus every feature the demo video shows; Present mode is a presentation of Stage, not a teacher dashboard | Owner, 2026-10-22 |
| D-40 | Paid runs are raised one at a time; the caps stay hard stops and the owner edits `.env` | Owner, 2026-10-22 |
| D-43 | The Kit's stylesheet is exempt from the CSS audit only by identity and exact text; CSS counters and `@counter-style` are refused at L0 for Kit pages | kit-guardian W3 review; D-37 class |
| D-42 | A covered question is answered from the library (an exact repeat, or a topic the local router recognises at 0.55 or more) before anything is paid for; every hit goes through the gate | P5 exit criterion; measured on the golden set |
| D-41 | L4 reads the Plan's words in the pipeline and is claimed only when a real judge passed them; the Free lane is a labelled last resort that needs that judge; a Kit gap log; L4 has its own pinned case set apart from L6 | Owner asked for both together; `page-false-prose`; hard constraints 1, 3 and 9 |

---

## 8. Open Questions

Unresolved. Anything marked `ASSUMED:` is a working assumption, not a confirmed fact. Confirm before anything load-bearing is built on it.

1. **A-1 ASSUMED:** the lane names and their labels (`kit-verified`, `model-checked`) are the agent's elaboration of the owner's idea.
2. **A-2 ASSUMED:** the Kit API shape (observables; `readout` accepts only observables) and the size guess (about 40 ui, 120 scene, 25 interaction, 150 to 250 science, 25 pedagogy). The P0 census and P1 spikes replace them.
3. **A-3 ASSUMED:** L1, L3 and L6 are designed, not built, and their detection power is unknown.
4. **A-4 ASSUMED:** Kit composition shrinks output to 1k to 2.5k tokens and cost well below the v3 figure of about $0.19. Arithmetic from stated prices, not a measurement. Measured at P3.
5. **A-5 ASSUMED:** the oracle ladder (registered, evidence-derived, cross-derived, declared) and the bet that textbook worked examples can serve as an independent reference. Corpus text quality and worked-example density are unmeasured. Four Chemistry experiment books are image-only PDFs and are not indexed.
6. **A-6 ASSUMED:** trust-ladder names, and that Arcana v2's `promoted` (three deliveries) is replaced by a human `reviewed` state.
7. **A-7 ASSUMED:** Peek, Stage, Companion and Shelf, and an MCP-Apps-shaped bridge, informed by OpenAI's patterns. Not confirmed by the owner. **Correction (2026-10-16 research):** the sources support inline, fullscreen and picture-in-picture modes and a preference for starting inline and avoiding nested scrolling; they do NOT show an official OpenAI limit of two actions. Peek's "at most two actions" is our own design rule. The research rests on search summaries, not primary pages.
8. **A-8 ASSUMED:** the corpus can be used locally and quoted briefly with citation in a public product. The legal position is unconfirmed. Confirm before any public deploy.
9. **A-9 ASSUMED:** dense embeddings are not needed at first.
10. **A-10 ASSUMED:** verification runs generated HTML in headless Chromium inside a no-network container for a public deploy. `node:vm` is not isolation. P1 spike (2026-10-16, `refdocs/evidence/2026-10-16-p1-isolation-spike.md`): partly confirmed. The harness verifies with no network under `unshare --net` at no measurable cost; `RLIMIT_AS` breaks Chromium; a browser exploit is not addressed. The hosting option is chosen at the deploy gate.
11. **A-11 ASSUMED:** the owner's "public students, no accounts" and "single user, no auth, no rate limit" are read as: designed for no-accounts student use, operated by one person, with a deploy gate that blocks public exposure.
12. **A-12 ASSUMED:** Python 3.13 and pnpm 10 (installed on the dev machine) are the pinned toolchain.
13. **A-13 ASSUMED:** English first with string tables from P0; Bahasa Melayu in P7 for reviewed environments (not asked in the interview).
14. **A-14:** the name "Synapse" collides with a published 2026 paper using SYNAPSE for an AI tutor. Decide before any public URL.
15. **A-15:** the deploy target is undecided. Decided in P7.
16. **A-16 ASSUMED:** the dev machine's lack of Docker and Postgres persists; SQLite locally, a managed database at deploy.
17. **A-17 ASSUMED:** the "Mark 2" the owner means is the Arcana v2 GenUI pipeline (D-31, D-36, D-41) together with the compiled-vault plan its docs literally name `genui-obsidianmark2` (D-35).
18. **A-18 ASSUMED:** `security-reviewer` is added before any public deploy; `test-runner` was not selected and tests are run by the session.
19. **A-19 ASSUMED:** the writers of the Environment store are trusted until the deploy gate; the gate does not re-render and rows carry no signature. See `DECISIONS.md`.
20. **A-20 CONFIRMED by the owner (2026-10-16):** the L6 planted-physics suite (detection rate of the verifier) and the per-micro-model registration suite (hard constraint 6) are separate; both are built.

---

## 9. Glossary

| Term | Meaning |
|---|---|
| Environment | The learner-facing artifact; delivered only as a verifier-minted type |
| Model | The declared science an Environment's numbers come from |
| Quantity | A named, unit-bearing, range-bounded value |
| Relation | A curated, evidence-cited rule over Quantities (equation, law, process, fact) |
| Micro-component | The smallest reusable unit of the Kit |
| Science micro-model | A micro-component that carries truth: cited, referenced, tested |
| Kit | The versioned library of micro-components, served at `/vendor/kit/<semver>/` |
| Observable | A reactive value; the only thing a readout accepts in Compose |
| Lane | Instantiate, Compose or Free |
| `dev-fixture` | A P0-only trust label for hand-written fixtures. It promises nothing about correctness. It is the only label the verifier can mint in P0, and it is removed in P1 when L1 and L3 make `kit-verified` reachable |
| Label | The trust label shown to the student: `kit-verified`, `model-checked`, then `reviewed`, `canonical` |
| Prompt pack | A versioned file of prompt segments selected per request |
| Mint | The single place that can create the deliverable type |
| Gate | The delivery path that re-derives, re-hashes and re-checks the stored record |
| Presentation | Peek, Stage, Companion or Shelf |
| Census | The P0 table of what each of the 53 topics needs from the Kit |
| Gap backlog | The ordered list of missing micro-components, from Free generations and part gaps |
| Mark 1, 2, 3 | v3's generation; Arcana v2's pipeline and vault; this repo's pipeline |
