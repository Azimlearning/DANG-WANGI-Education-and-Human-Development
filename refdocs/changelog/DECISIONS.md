# Architectural Decisions: Synapse v4

> Record decisions here so they aren't re-debated in future sessions.
> Format: **Decision**, **Why**, **Trade-offs / what was rejected**.
> Canonical one-line list lives in `refdocs/synapse-v4-PRD.md` section 7; this file expands the load-bearing ones under the same id.

An ADR is worth writing when the decision (a) is expensive to reverse, (b) will look arbitrary to a future reader, or (c) had a real alternative someone will propose again. Everything else is just a commit message.

---

## D-01: "Environment" is the artifact term, with a five-part definition (2026-10-16)

**Decision.** The learner-facing artifact is an **Environment**: a verified, bounded, interactive space for one learning goal with a Model (the declared science), a Scene and Instruments (what is seen and observed), a Task with Scaffolds (what is asked, with hints), and Evidence (the textbook statements and the checks passed).

**Why.** Owner, 2026-10-16: "i think calling it enviroment is better then labs for synapse overall direction". "Lab" promises an experiment; KSSM students also need process explorers, data investigations, practical benches and exam rooms. One word covers all of them and points the engineering at the whole, not at one numeric function.

**Trade-offs / rejected.** "Lab" (narrower, and Arcana v2's lab was a single scalar function). "Environment" collides with process environment variables and virtualenvs: in code, `Environment` is the artifact only, process settings are "settings", and the artifact is never abbreviated to `env`.

## D-02: Raw HTML/JS stays the primary generated artifact, in three lanes (2026-10-16)

**Decision.** The generated deliverable is a raw HTML/JS document, as in v3. It is produced in three lanes decided by what verification the output survives: **Instantiate** (a stored or template-filled environment), **Compose** (the model writes HTML/JS that calls the Kit; primary for new questions) and **Free** (a whole document with no Kit).

**Why.** Owner, 2026-10-16, quoted exactly: "I agree with raw html stay primary like in v3 and that makes it more adaptive and generative". A fixed spec and runtime would have been easier to verify but would have capped what an environment could be. The lanes keep the adaptivity and make the trust difference between outputs explicit.

**Trade-offs / rejected.** *Data-first with raw HTML only at authoring time* (the founding brainstorm's recommendation): strongest verification, smallest code-execution surface, rejected by the owner. Its best parts survive: the Instantiate lane, the Kit's science micro-models as the source of truth, and the oracle ladder. *Keep v3 exactly*: rejected, because correctness was unmeasured and the cost was about $0.19 per artifact. **Cost of this decision:** correctness in the Free lane is the strength of v3 (an LLM verifier, unmeasured), and a Compose output can still show a misleading picture beside a correct number. Mitigations: honest labels (D-07), L1, L3 and L6 (PRD 3.3).

The lane names and labels are the agent's elaboration of the owner's idea (A-1).

## D-03: A Kit of hundreds of micro-components is an allowed building block (2026-10-16)

**Decision.** The generator may, and in the Compose lane must, build on a versioned library of micro-components (ui, scene, interaction, science, pedagogy, bridge), including audited science micro-models that carry the truth. This reverses v3's hard rule 4 ("no predefined component library for learning artifacts") in the form that rule was being violated by shipped builtin labs: micro-components are inputs the generator composes; whole pre-built labs are library *outputs*, not templates it must copy.

**Why.** Owner: "hundreds of micro-compenets since we know our topics and fields". Science is written and reviewed once and reused. It cuts output tokens (v3's examples repeat the same chrome in every file), improves visual consistency (v3's UX plan recorded the shell and artifact clashing), and moves correctness to where it can be audited.

**Trade-offs / rejected.** Authoring hundreds of micro-components with tests, and for science components reviewed references, is the long pole of the project. Mitigation: parameterise by interaction pattern, order the work by the gap backlog, and keep the Free lane open so the Kit is never a hard ceiling. Rejected: a closed component catalog that forbids free generation (v1's "12 concepts" ceiling).

## D-04: Mark 3 is prompt packs, the Kit and accelerator functions on top of Mark 2's lifecycle (2026-10-16)

**Decision.** The generation pipeline is called Mark 3. Mark 1 is v3's single-shot generation with an LLM verifier. Mark 2 is Arcana v2's template, fences, checking, save, reuse pipeline with its lifecycle (D-36, D-41 there) and compiled-vault plan (D-35 there). Mark 3 adds assembled prompt packs, Kit retrieval, and accelerator functions (library lookup, template instantiate, edit-not-regenerate, model tiering, prompt caching, skeleton first, early gates, deterministic repair, output budgets, overnight batch fill, canonicalisation, per-request budget).

**Why.** Owner: "a pipeline with prepade promps, hundreds of micro-compenets ... and other funtions to help generation more fast, cost saving and efficient, aracana v2 haa a pipeline or system for the gen ui which is at version mark2 we can enhance and make mark3". Arcana's own docs use "Mark 2" for the vault direction (`genui-obsidianmark2`); the pairing with its pipeline is the owner's phrase (A-17).

**Trade-offs / rejected.** Porting Arcana v2's data-typed pipeline unchanged: its generated part is one scalar function, which cannot express an environment. Only its discipline (lifecycle, planted defects, re-verify on reuse, honest limits) is carried.

## D-05: Python API + Next.js web + `packages/schema` + `packages/kit` (2026-10-16)

**Decision.** FastAPI on uv (Python 3.13), Next.js on pnpm, a TypeScript schema package with codegen to strict Pydantic, and a JavaScript Kit package built by esbuild and served as static files from `/vendor/kit/<semver>/`. Node is a build and test dependency, not a runtime kernel executor. Verification runs generated HTML in headless Chromium.

**Why.** Owner delegated: "You can decide fully, just which ever one is faster especial for the raw html components". The raw-HTML pipeline already exists in Python and is tested (post-processor, scan, verifier, gate, render harness, router, evals); Arcana v2's lifecycle, mint, store and mutation harness are Python; the ingestion and router-distillation assets are Python. The Kit is the only large new JavaScript surface and builds independently.

**Trade-offs / rejected.** *TypeScript end to end*: one evaluator shared by verifier and browser, but a rewrite of every port. Two languages mean a codegen seam, which Arcana v2 already solved.

## D-06: Sandbox and delivery gate carried over unchanged (2026-10-16)

**Decision.** The artifact iframe is `sandbox="allow-scripts"` only, never `allow-same-origin`. The injected CSP names the configured public origin explicitly. Scripts load only from `/vendor/` and `/vendor/kit/<semver>/` on our origin; no runtime CDN. Only the verifier module can mint the deliverable type; the gate re-derives, re-hashes and re-checks the stored record; the browser re-hashes before rendering.

**Why.** Hard rules of v3 and Arcana v2, proven in both. v3 found that in an opaque-origin `srcdoc` iframe `'self'` matches nothing, so an artifact CSP of `script-src 'self'` blocks our own vendored libraries: the CSP must name the origin. Arcana v2's mutation suite and two independent reviews found no bypass of its gate (a claim about that set, not a proof).

**Trade-offs / rejected.** `allow-same-origin`, a runtime CDN, evaluating generated code in the host page: forbidden. `node:vm` is not presented as isolation.

## D-07: The Free lane is served with an honest label, never `canonical` unreviewed (2026-10-16)

**Decision.** Free-lane output is served to students labelled `model-checked`, queued for human review, and logged as a Kit gap candidate. A setting can switch it to hold-for-review.

**Why.** Owner chose "Serve with an honest label". It keeps v3's adaptivity without regressing it, and the label states a real difference in strength.

**Trade-offs / rejected.** *Hold for review*: safest, but the product would answer only what the Kit and library already cover. *Serve unlabelled*: hides a real difference. **Risk:** the Free lane's accuracy is unmeasured; a memorised wrong model persists (stimulus S8 in the v3 idea work). L6 measures the verifier before this is relied on at scale.

## D-08: Fakes by default; the owner confirms every paid run; a monthly cap (2026-10-16)

**Decision.** Everything runs on a deterministic fake LLM unless `SYNAPSE_LLM_MODE=live`. A paid run (evaluation, ingestion, generation sweep) states a projected amount and waits for the owner. Every paid call goes through the LLM seam and the spend ledger and is refused before sending if it would exceed `LLM_MONTHLY_CAP_USD`.

**Why.** Owner chose "Fakes by default, confirm each paid run". v3 and Arcana v2 both worked this way and both found real defects in it (an unledgered path; a credit balance separate from the cap).

**Trade-offs / rejected.** *Live by default under a hard cap*: faster iteration, but a bug can spend up to the cap. *Fakes only until P3*: delays the first real measurement.

## D-09: The first vertical is decided by the P0 coverage census (2026-10-16)

**Decision.** No subject or chapter is chosen for the first end-to-end vertical until the P0 census of the 53 topics is complete. The walking-skeleton environment in P0 is an illustration and is not the first vertical.

**Why.** Owner: "Let the census decide". The earlier estimate (about 11 of 13 Physics, 3 to 4 of 13 Chemistry, 2 to 3 of 27 Biology) was a judgement, never measured.

**Trade-offs / rejected.** Starting with Physics (the strongest verification) or the Chemistry titration bench (the best Kit stress test): both plausible, neither chosen blind.

## D-10: `git init` here and ignore this folder in the monorepo; docs are self-contained (2026-10-16)

**Decision.** This folder is initialised as its own repository now and listed in the Genui monorepo's `.gitignore`, the same pattern as the nested `MCAIT/` repository. All docs avoid relative links outside this folder; sources are cited by repo, path and commit.

**Why.** Owner: "i think either one or two is good its just that later i will only open the v4 project file so no other file will be affected". A plain `git rev-parse` inside the monorepo finds the parent and would silently skip `git init`.

**Trade-offs / rejected.** Leaving the folder tracked by the monorepo (an embedded-repo warning). No git yet (the owner would have to remember).

## D-11: No accounts; single operator; no auth, no rate limit; public exposure blocked until a deploy gate (2026-10-16)

**Decision.** The product is designed for students with no accounts: progress and saved environments live on the device and no student personal data is stored server-side. It is operated as a single-operator tool with no authentication and no rate limiting. The API must not be reachable from the public internet until the deploy gate in `refdocs/guides/checklist.md` is met and recorded.

**Why.** Owner: "Basically number 1 is what i want but single user so no auth no rate limit and such" (number 1 was "Public students, no accounts"). The two statements pull apart: a public URL with unauthenticated generation is a cost and abuse exposure (the v3 idea work called this out as a decision only the owner can size). Resolved by building as the owner asked and recording a gate rather than silently ignoring the exposure. Arcana v2 took the same stance (its D-04: a single-user tool, "do not expose it").

**Trade-offs / rejected.** Building limits and isolation first (slower, not requested). Treating "public" as launched (unsafe). See A-11: this reading is the agent's and needs the owner's confirmation.

## D-12: No graph retrieval; BM25 or TF-IDF first; dense embeddings only if measured to help (2026-10-16)

**Decision.** Retrieval over the fixed KSSM corpus is flat (BM25 or TF-IDF, as in v3's `ml/rag`) with the topic taxonomy for routing. No GraphRAG, no trained re-ranker.

**Why.** Arcana v2 measured, with the protocol fixed first, that graph retrieval is not shown to beat flat (pooled nDCG@10 difference -0.001, p = 0.69, 38 questions) and that a pretrained re-ranker was not shown to help (D-37 there). The Synapse corpus is small and curated.

**Trade-offs / rejected.** GraphRAG (v1 and v2's core). What is kept from the vault direction is the *claims* idea: verbatim sentences a passage states, usable as evidence and as cloze questions with no model call.

## D-13: Process: this doc system, three subagents, and the secret guard only (2026-10-16)

**Decision.** The `refdocs/` doc system with mandatory changelog, ADRs and plan/execution pairs. Subagents: `doc-keeper` (always), `cost-auditor`, and `kit-guardian` (custom, read-only review of micro-component, wire and prompt-pack changes). One hook: the secret guard on `Write|Edit|MultiEdit`. No other hook until a rule has been broken.

**Why.** Owner chose `cost-auditor` and `kit-guardian`; `doc-keeper` is the skill's always-on agent. The expensive silent failures here are a key committed to a public repo, a paid call outside the seam, and a Kit change that skips its registration suite.

**Trade-offs / rejected.** `test-runner` (not selected; the session runs the suites), `ui-reviewer` (not selected; accessibility is a registration-suite item), `security-reviewer` (added before any public deploy, A-18). An invariant-guard hook comparing Kit sources with the manifest: written as prose in preflight question 5 until it has been broken once.

## D-14: The corpus is local and gitignored; a manifest and ingestion script are committed (2026-10-16)

**Decision.** KSSM textbook PDFs and every extracted passage file stay out of the repository. A manifest (file names, hashes, subject, form) and the ingestion script are committed. The product quotes short cited spans only.

**Why.** The textbooks are Ministry of Education works and this repository becomes public. The legal position on quoting passages in a public product is unconfirmed (A-8).

**Trade-offs / rejected.** Committing extracted passages (convenient, and a likely licensing problem). A reproducible corpus then depends on the owner having the PDFs locally.

## D-15: Live mode needs only an Anthropic key and a cap, and no live provider exists until P3 (2026-10-16)

**Decision.** `SYNAPSE_LLM_MODE=live` makes startup require `ANTHROPIC_API_KEY` and a positive `LLM_MONTHLY_CAP_USD`, and name whichever is missing. `OPENROUTER_API_KEY` is optional. In P0 the factory builds only the fake provider; asking for live builds nothing and raises `ProviderUnavailable`.

**Why.** CLAUDE.md names OpenRouter as an optional fallback, and Arcana v2's rule of requiring both keys would have blocked a live start for no reason. Building a live provider before P3 would put a paid path in the repo that no one has confirmed (hard constraint 8, CLAUDE.md rule 7).

**Trade-offs / rejected.** Requiring both keys (stricter, blocks a single-provider setup). Building the Anthropic provider now behind the cap (convenient, but untestable without a paid call and out of P0 scope). Cost: live-mode configuration is validated at startup but has no provider behind it until P3, so a valid live config still fails at the first request.

## D-16: The Kit's semver is tied to its bundle bytes, and stored Environments carry the bundle hash (2026-10-16)

**Decision.** `packages/kit/kit-lock.json` (committed) records the SHA-256 of each released Kit version's `core.js`. The build fails if a locked version's bytes change, and says to bump `KIT_VERSION` and the package version. `--relock` replaces an entry and is for an unreleased version only. Each Environment records the bundle hash it was verified against, and the delivery gate refuses it as `stale_kit` if the built bytes differ.

**Why.** Hard constraint 6: a behaviour change bumps the Kit semver, which marks stored Environments stale. Before this, nothing tied the version string to the code: a changed bundle under the same version left every stored Environment trusted (kit-guardian S2). The review found it by tracing the code.

**Trade-offs / rejected.** Any source change that alters the minified bundle now forces a bump or a visible `--relock`, including an esbuild upgrade (the bundle is only reproducible with the pinned esbuild). Rejected: hashing the source tree instead (misses build-time changes), and trusting a test that pins the version string (it detected nothing).

## D-17: The CSP must be the first element of the document, ambiguous markup is refused, and verification presses real input (2026-10-16)

**Decision.** Post-processing strips HTML comments and refuses any other markup declaration or processing instruction (`<![CDATA[`, `<?xml`, a stray `<!`). It injects the CSP right after the `<head>` start tag found by an HTML tokenizer, then requires `csp_is_first`: exactly one CSP, ours, with only a doctype and `html` and `head` start tags before it. The delivery gate runs the same check on the stored HTML. The render harness presses real pointer and keyboard input, treats any navigation of the frame as a refusal, fails closed if it loses the page, and the web host tears down a frame that loads a second time.

**Why.** kit-guardian B1 and B2, both reproduced. A `<head>` inside a comment put the CSP in an inert comment, so a document with a hidden `eval` passed every layer. A bare `location = '//evil.example'` passed the scan, CSP does not govern navigation and `sandbox="allow-scripts"` still lets a frame navigate itself, and the harness never fired a pointer event.

**Trade-offs / rejected.** Some legal HTML (comments, an XML prolog) is now refused or altered; generated Environments do not need either. Rejected: a regex for the first `<head` (the original bug), and banning only `location` assignments (obfuscation `window['loc'+'ation']` passes a text scan). **Residual risk:** a navigation or request that fires only on a condition the harness never reaches still passes the verifier; the host teardown and CSP limit the damage but the request to the external origin has already been made. Only isolation (A-10) closes it.

## D-18: The first vertical is Physics Form 5, chosen by the agent under the owner's delegation (2026-10-16)

**Decision.** The first vertical is Physics Form 5: `force_and_elasticity`, `forces_and_pressure` and `electricity`. This resolves D-09 provisionally.

**Why.** Owner, 2026-10-16: "for now u can choice any suitable one". The census (an estimate) ranks Physics first. Within Physics it favours Form 4 on the count of strong topics, but Form 5 starts from `mechanics.hookes`, which already exists and has a registration suite, and its three topics are the simplest closed forms in the table with the least custom drawing (springs, bars, circuit symbols). The cheapest route to the first fully verified result is the right start; Form 4 follows in P4.

**Trade-offs / rejected.** Physics Form 4 (more strong topics, but orbits, wave patterns and ray diagrams need scene components that do not exist). Chemistry (second-ranked, thinner base of reusable models, heavier scene burden). **Revisit freely:** the owner delegated this and may overturn it at any time; the census stays an estimate and the Physics Form 4 topics stay in P4.

## D-19: The end state is at least nine verified Environments, three per subject, each tied to a catalogued KSSM experiment or topic (2026-10-16)

**Decision.** At the end of the build there must be many more Environments than the walking skeleton, and at minimum three each for Physics, Chemistry and Biology (nine in all). Each is composed over the Kit, passes every deterministic layer, carries its honest label and `checked` record, and is mapped to a row in a new **experiment catalogue**: one record per KSSM practical experiment or activity, with the Amali fields (problem statement, hypothesis, manipulated, responding and fixed variables, procedure, results) and the topic it belongs to. The catalogue is a module of its own: the schema, the validator and the ingestion tooling are built in the cloud; the text-derived fields are filled locally from the textbooks, which are not in any repository. Titles seeded in the cloud are marked `unverified` until checked against the textbook.

**Why.** Owner, 2026-10-16: "at the end of the project dev there should be a lot of experiments or environments to be generated (minimum like 3 from each subject, also we have docs of all the available exp)". The experiment is the unit KSSM students are examined on (SPM practical tests), the unit N5 Amali mode needs, and a better coverage unit than a topic.

**Trade-offs / rejected.** Counting by topic only (loses the practical the student sits). Seeding the catalogue from the textbooks in the cloud (impossible: not present; copyright, D-14). **Limit:** until the corpus exists locally, cloud-built Environments cannot reach `kit-verified` (hard constraint 4), so the nine are honest at `model-checked` until their citations are verified.

## D-20: A models track: small trained local models, measured before they may gate anything (2026-10-16)

**Decision.** A new module (`api/models` for inference, `eval/models` for training and evaluation) holds trained local models. First kinds: (1) a **multi-head router** predicting topic (53-way), domain, artifact pattern and complexity from the question text, trained on the v3 labeled dataset (committed in GenUI-Education, no paid call); (2) a **misconception matcher**, built as retrieval over the misconception list, not trained, because the list is too small to train on. Rules: every model is evaluated on held-out data against stated baselines (majority class and a keyword rule) before use; a confidence threshold is chosen on validation data and below it the LLM router decides (PRD 3.2 stage 1); artifacts are JSON weights, never pickles; each model has a model card in `refdocs/evidence/` with its data provenance, metrics, limits and how to retrain; training is deterministic (fixed seeds) and free.

**Why.** Owner: "a new added component which is a trained model (a few different kinds if needed)". IDEA-0003 (distilled router) was in the enhancement plan and the PRD's Route stage, but the PRD had no module, data or evaluation plan for it. The v3 Keras student reached 88.1 percent domain and 70.4 percent artifact-type accuracy and ran only in shadow mode.

**Trade-offs / rejected.** A neural or embedding model (heavier; A-9 and D-12 say embeddings only if measured to help, and the download may not work here; listed as a local follow-up). Labels come from an LLM teacher with a known self-disagreement rate, so measured accuracy is agreement with the teacher, not with truth; the model card says so. Training a lane or Kit-fit predictor (no data until P3 produces generation logs).

## D-21: What a label means before the corpus exists (2026-10-16)

**Decision.** `model-checked` means: the Environment passed every deterministic layer (L0 scan, render and fuzz, L1 provenance, L3 numeric cross-check) but has no verified textbook source. `kit-verified` additionally needs a citation whose quote was verified against the corpus (P2). `dev-fixture` is removed in P1 and is no longer mintable. `reviewed` and `canonical` still need a human. A Free-lane Environment is at most `model-checked` (D-07) and only with L4 and render passes.

**Why.** Hard constraint 4: where no source exists the label says so and the output cannot rise above `model-checked`. Without a definition, the nine cloud-built Environments (D-19) would have no honest label to carry. The names are the agent's elaboration (A-1).

**Trade-offs / rejected.** Keeping `dev-fixture` (it promises nothing, so it cannot carry real work). A new label name such as `checked-unsourced` (more precise, but the name `model-checked` is already in the PRD, the schema and the web labels; the precision goes into the definition and the provenance text instead).

## D-22: Cloud-first, local last (2026-10-16)

**Decision.** Do as much development as possible in the cloud session and move to a local Claude Code session at the end. Anything the container cannot do is noted, not worked around, and listed in the "Deferred to local" register in `refdocs/STATUS.md`, which is the hand-off. The register's current categories: textbooks and OCR (not in any repo), the owner's decisions and consents, paid runs and keys, Windows-specific verification, and model downloads this container cannot make.

**Why.** Owner, 2026-10-16: "i want todo as much dev as possible in cloud at the end i will move to local".

**Trade-offs / rejected.** Working around a limit with something that looks like the real thing (for example inventing textbook content). Stopping at the first limit. **Cost:** some work built in the cloud will need re-checking locally (Windows paths, a real corpus), which the register records.

## D-23: The Mark 3 pipeline is layered and skeleton-first: plan as data, assemble deterministically, fill only the gaps (2026-10-16)

**Decision.** The pipeline is eleven ordered layers (intake, route, look up, plan, plan checks, skeleton, assemble, fill, verify, mint and gate, deliver, learn; PRD 3.2). The model's main output is a validated **Plan** (data). A deterministic **assembler** builds the page from a per-pattern **skeleton**; the model writes only short typed **slot fills** for parts marked `custom`. A **fail-check registry** names every refusal (code, layer, repair route, model hint, student message) and a test ties it to the code. Prompt packs are versioned files assembled in cache order. The student gets a **loading skeleton** (the Peek shell from the Plan) before verification finishes. The Kit manifest gains a `useWhen` sentence per component and the kit pack is chosen by retrieval over it. A degrade ladder (Instantiate-by-plan, Compose with fills, Free labelled, text) means no blank screen.

**Why.** The owner asked for a layered pipeline with skeletons, deep prompt templates, fail checks and micro-components that make generation easier and cheaper. The research (`refdocs/evidence/2026-10-16-chatgpt-ui-research.md`) shows ChatGPT's reliability comes from the model supplying data to a developer-authored template, and declarative systems (A2UI, AG-UI) make a trusted catalogue the security boundary. Moving the model's output toward data removes most of what the verifier would otherwise have to catch and most of the output tokens.

**Trade-offs / rejected.** Skeletons are rigid: questions they cannot express become `custom` slots or the Free lane, and the rates are tracked as the Kit backlog (principle 8). Rejected: having the model write the whole page by default (v3, expensive and the largest verification surface); a fully declarative JSON tree like A2UI (cannot express the virtual-experiment glue we need). The new layer is named the **assembler** to avoid the PRD's Composer, which places blocks in the UI (hard constraint 5). The research rests on search summaries, not primary pages; the cost and latency benefits are assumptions until the first paid run measures them (A-4).

**Amendment (2026-10-21), the decision stands, one premise is narrowed.** The "Why" says ChatGPT's reliability comes from "the model supplying data to a developer-authored template". That describes the Apps SDK only. OpenAI's release notes of 2026-10-07 describe Intelligent UI, where the model itself chooses and composes the interface, reportedly from a platform-owned component library with a streaming compiler. Both designs put a vetted catalogue between the model and the pixels, which is what D-23 adopts, so nothing here is reversed. What changes is the precedent: a first-party, model-composed, catalogue-bounded UI now exists, which supports the Compose lane. Details, evidence types and unknowns: `refdocs/evidence/2026-10-21-chatgpt-intelligent-ui-rea.md`. The DIL, `AppBlock` and sandbox internals in that note come from one competitor's reverse engineering and are unverified; no assumption in this ADR depends on them.

---

## D-24: The page's numbers are protected in four places, and none of them alone is a proof (2026-10-16)

**Decision.** Generated code runs in the same JavaScript realm as the Kit, so the audit is only as strong as what protects it. P1 uses four layers together: (1) **lockdown**: the Kit freezes the JavaScript and DOM intrinsics (`Array`, `RegExp`, `Map`, `Node`, `Element`, ...) at the end of its own bundle, before any generated script runs, and reads the page only through DOM functions it captured at load (`packages/kit/src/dom.ts`, `lockdown.ts`); (2) **ownership**: every element and spoken attribute the Kit makes is registered with the text it must hold, observables are frozen, and option strings are copied at call time; (3) **the verifier**: the browser harness audits at load, across every grid and extreme position, and at the end, and Python recomputes each value from independent references (`api/verify`); (4) **the runtime self-check**: the Kit re-audits itself with a MutationObserver and a timer in the student's browser and tells the host, which closes the Environment (`packages/kit/src/watch.ts`, `web/components/EnvironmentFrame.tsx`). The audit also refuses anything that can draw a number without a text node (canvas, media, list counters, CSS images and generated content, fonts, look-alike widgets), numbers in non-ASCII digits, and models fed in the wrong unit.

**Why.** The kit-guardian review of P1 minted eighteen attack pages against the first design, all `model-checked`: built-ins patched to blind the audit, a readout overwritten only on a touch screen or after a minute, copy numbers hidden behind the word "step", a canvas built from string pieces. Patching the individual holes does not end the class; the class is "the page can act before and after the moments the harness looks". Freezing the realm stops tampering with the audit; the self-check turns "the harness never reached that branch" from a gap in the guarantee into a hidden Environment.

**Trade-offs / rejected.** Freezing built-ins breaks code that patches them (polyfills, `Object.prototype` assignment of inherited names); generated Environments do not need to. The self-check can false-alarm if the Kit's own rendering drifts from its expected text, which would close an honest Environment; the tests pin that an honest page stays quiet. Rejected: running the audit from a separate browser world (CDP isolated world): it cannot see the Kit's private registries, so it would need a second ownership channel the page could also read. Deferred to the A-10 / deploy-gate work: a host-side check of the DOM from outside the frame. **Limits that remain:** the self-check and lockdown are defence in depth, not a sandbox proof; a browser or engine bug defeats them; the audit compares numeric values and units, not meaning (a correct number beside a misleading picture); a condition the harness never creates is covered only at student time, and the Environment is already on screen for the moment before the check fires (interval 1 s, mutation debounce 50 ms).

## D-25: `kit-verified` is reachable only when the corpus re-proves every citation (2026-10-16)

**Decision.** `guard_label` (mint) and the delivery gate refuse `kit-verified` unless the lane is not Free, the Environment cites at least one source, every citation is marked verified, and an `Evidence` object can find each quotation in the local corpus (exact match after normalisation of case, whitespace and hyphenation). A citation that claims `verified` but cannot be re-proved is refused as `citation_unproved`, not downgraded. With no corpus configured the best label is `model-checked` with an explicit UNVERIFIED citation. `reviewed` and `canonical` are never mintable by code.

**Why.** Hard constraint 4 says no source, no `kit-verified`. A flag on the record is a claim; the corpus lookup is the proof, and the gate repeats it so a row edited in storage cannot gain the label. Exact-after-normalisation matching is deliberately strict: a paraphrase is not a quotation.

**Trade-offs / rejected.** The corpus is local and never committed (rule 13), so the cloud build can only prove the mechanism against a synthetic corpus. Rejected: fuzzy matching (it would accept a nearby but wrong passage), and trusting the planner's citation field. Limit: a quotation proves the words are in the book, not that the Environment's formula matches them.

## D-26: Lane names mean what was done for this question (2026-10-16)

**Decision.** A page the pipeline planned and assembled for the student's question from audited Kit parts is **Compose**, with or without model-written slot fills. **Instantiate** is a stored, hand-written Environment reused as it was (fixtures, the P4 breadth set). **Free** (a whole model-written page) is not built. The student sees this in the provenance panel ("planned for your question and assembled from audited Kit components"). If a page with fills is refused by the verifier, the fills are dropped and the plain assembly is verified once before the student gets words only.

**Why.** The P3 review found fresh pages shown as "a stored Environment, not written for this question", which is false. The PRD says the lane is decided by what verification the output survives; a library hit keeps the lane it was minted with.

**Trade-offs / rejected.** "Compose" now covers plan-only pages where no model wrote any code, which stretches the PRD's wording ("raw HTML/JS that calls the Kit"). Kept because the label's promise (assembled from audited parts, checked) is exactly true. Rejected: a fourth lane name (more vocabulary for the student with no new trust meaning).

## D-27: The library is a question cache in front of the pipeline, and every hit goes through the gate again (2026-10-16)

**Decision.** `canonical_question` maps a question to a stored Environment id (`questions` table). A hit is delivered by `deliver` (re-hash, re-scan, CSP, Kit sha, label guard, evidence re-proof, withdrawn check), so a withdrawn, stale or tampered row falls through to a fresh run. Lifecycle is `withdraw` / `restore` and `flag` (a student or the operator marks a problem); `library()` lists rows with their state; an Environment verified against an older Kit bundle is `stale`.

**Why.** Most KSSM questions repeat; a hit costs nothing and the hard constraint (nothing unverified reaches the client) still holds because delivery does not trust the cache. 

**Trade-offs / rejected.** Exact canonical match only; no semantic cache until measured (a wrong near-match is worse than a miss). Single operator, so no per-user state (D-11).

## D-28: A local `none` topic is never trusted (2026-10-16)

**Decision.** When the router predicts `none` for the topic head, the question goes to the LLM fallback regardless of confidence. A keyword second opinion was measured and is no better than chance on the `none` class, so it is not used.

**Why.** 7 of 24 golden questions were wrongly routed to `none` by the local model (the training data's untagged rows include on-syllabus questions). A wrong `none` silently becomes "words only" for a question the product exists to answer.

**Trade-offs.** More fallback calls (cost) for questions that really are off-syllabus. Revisit when the local dataset is relabelled (deferred to local).

## D-29: Kit 0.1.0 stays unreleased and is relocked until the deploy gate; Kit files revalidate (2026-10-16)

**Decision.** Until the owner releases, every Kit change relocks 0.1.0 (`build.mjs --relock`); stored Environments verified against an earlier build become `stale_kit` and are re-verified rather than served. Kit files are served with `Cache-Control: no-cache` so a browser cannot keep an old bundle under the same semver. At release the version is bumped and files can be made immutable.

**Why.** D-16 ties semver to bytes. Bumping on every pre-release edit would leave dozens of dead versions; relocking is safe only because nothing is public yet.

**Trade-offs.** The lock file does not protect an unreleased version. A cached stale bundle would break the page's hash expectation, hence the header.

## D-30: Plan checks know cross-quantity rules and topic fit; prompt packs keep per-request text below the divider (2026-10-16)

**Decision.** `plan_checks.RELATIONS` holds rules a per-quantity domain cannot express (first: dilution final volume must not start below the starting volume, PLAN-015). PLAN-016 refuses a model used under a topic its Kit entry does not list. The prompt loader refuses any `{{variable}}` above the `=== VARIABLE ===` line unless the pack lists it in `static_inputs` (a value that is constant between requests, such as the failure-mode list).

**Why.** The P3 review found plans the verifier would accept as numbers but that make no physical sense, a model answering under the wrong topic, and cache prefixes that changed on every call. Each is now a check with a test.

**Trade-offs.** Relations are written by hand per model; a new model with a cross-quantity constraint must add a line (a coverage test for this does not exist yet).

## D-31: Stored Environments are signed with an HMAC, and the gate refuses an unsigned or altered row when a key is set (2026-10-16)

**Decision.** `STORE_ATTESTATION_KEY` (a secret outside the data directory) signs, at `put_verified`, an HMAC-SHA256 over the id, title, lane, label, Kit version and sha, HTML hash, citations, plan summary and the `checked` record. The signature is computed from what the verifier just minted, never from what is already in the row. `deliver` calls `attestation_ok` first and refuses with `unattested` (GATE-006) a row with no signature, a wrong key or any altered signed field. With no key, behaviour is unchanged and A-19 stays open (single operator, D-11).

**Why.** The gate re-hashes, re-scans and checks the CSP and Kit, but cannot tell a row the verifier wrote from one written straight into the SQLite file. A signature with a key the file writer does not hold closes that, which hard constraint 1 needs before the API is public.

**Trade-offs / rejected.** The HTML itself is covered through its hash, which is signed. Rotating the key makes older rows `unattested` and they must be re-verified. Rejected: re-rendering on delivery (adds seconds and a browser to every request; kept as a later option for high-risk deploys). Limit: someone who steals the key can sign anything, so the key belongs in the host's secret store, not in `.env` in the repository folder. Lifecycle, flags and the question cache are decisions about rows, not Environments, and are not signed; the gate still re-checks `withdrawn` on every delivery.

## D-32: The offline file is a separate artifact that carries the Kit, checks two hashes before it runs, and keeps the exact sandbox (2026-10-16)

**Decision.** `GET /library/<id>/export` returns one HTML file for a school PC with no network (`api/export.py`). It is built only from a block the delivery gate just returned, plus the bytes of the Kit bundle the Environment was verified against. The file embeds both as data with their SHA-256 values; its own script re-hashes both and runs nothing on a mismatch (it says so in words). The Environment runs in `<iframe sandbox="allow-scripts">` with no `allow-same-origin`; the Kit is placed inline in that frame's document because an opaque-origin frame has no `/vendor/` to fetch from. The provenance (label, lane, source, what was checked, limits) is printed in the file. A withdrawn, stale or tampered Environment is not exported, because the gate refuses it first.

**Why.** Reach for schools without reliable internet is a P7 goal. The hard constraint that scripts load only from `/vendor/` is about trusting where code comes from; an inline script whose bytes equal a hashed, locked Kit bundle keeps that intent, and the wrapper's own CSP (`default-src 'none'`, no `connect-src`) keeps the page from talking to anything.

**Trade-offs / rejected.** A saved copy cannot be updated, withdrawn or fixed once someone has downloaded it; the file says so. The hash check runs in the file's own script, so someone who edits the whole file (script included) defeats it; the check protects against accidental damage and a changed payload, not against a person who rewrites the wrapper. Rejected: shipping the file without the check (no integrity at all), and loading the Kit from a CDN (needs a network). Not built: chapter packs (many Environments in one file) and signing the file.

## D-33: Progress is device-local, counts only the first answer, and is described in words (2026-10-16)

**Decision.** The Kit's `conceptCheck` tells the host how the student's FIRST answer went (`synapse_event`, control `concept_check`, value `correct` or `incorrect`). The web host keeps, per Environment id, the number of tries and correct answers in `localStorage` (`web/lib/progress.ts`), shows them as "Just started", "Getting there" or "Secure" (`Secure` needs at least two right answers and 70 percent), and offers an export code (`SYN1.<base64url JSON>.<checksum>`) to move it to another device. There is no account, no server copy, no analytics.

**Why.** P6 asks for a learner map without accounts (D-11, public students). Counting only the first answer stops a student from guessing through the options and being scored as secure. A percentage from two or three answers would claim more than it knows, so the label is in words with the raw counts beside it.

**Trade-offs / rejected.** The record is the student's own and is editable (the checksum only catches a mistyped code), so nothing may depend on it being true: it is for the student, not for a teacher or a grade. A generated page could in principle post a fake event; the scan forbids `postMessage` in generated code and the Kit owns the bridge, but the data is self-regarding anyway. Storage can be blocked or cleared: every access is guarded and the app works without it. Rejected: a server-side learner profile (needs accounts and consent), and spaced repetition scheduling until there is real usage data.

## D-34: Live mode builds the Anthropic provider; a billed reply we reject is booked at its real usage; tests may only touch this machine (2026-10-18)

**Decision.** (1) `build_llm_service` in live mode runs the same prerequisite check as the ledger (key, positive cap, absolute ledger path) and then builds one `AnthropicProvider` with no fallback (OpenRouter is not built); there is no uncapped live path. This supersedes the "no live provider until P3" part of D-15. (2) `ProviderFailure` can carry `tokens_in` and `tokens_out`. The Anthropic provider sets them when it received a real reply and then rejected it (`stop_reason` `max_tokens`, `refusal`, or no text), and the service books the cost of those exact tokens. Where the provider has no usage (a timeout), the old rule stands: the estimated input cost. (3) A repo-root `conftest.py` makes every test refuse a connection or a name lookup to anything but a loopback host.

**Why.** (2) The first design booked only the estimated input for a truncated reply. Anthropic bills the output too, and on Opus 5.5 that includes thinking tokens, so a reply that ran to a large `max_tokens` would have been billed in full while the ledger recorded only its input (a 16,000-token Sonnet 5.5 reply is $0.16 against about $0.001 booked), and the monthly cap would not have held. (3) On 2026-10-18, wiring the provider made an existing live-mode route test (dummy key) send a real request to api.anthropic.com; the API answered 401 and nothing was billed, but a test must never open an outside connection, and only a test that opted into `no_network` was protected.

**Trade-offs / rejected.** Booking the exact usage trusts the provider's `usage` field (the service already took the larger of reported and computed cost on success). The guard's failure is an `AssertionError`, deliberately not an `httpx` error, so no retry or fallback path can convert it into a quiet "transient" failure. Rejected: raising `max_tokens`-style estimates for every failure (over-reserves on honest 5xx errors), and relying on each test to remember a fixture. On Windows the standard library emulates `socketpair` with a loopback connect, which the stricter `no_network` fixture exempts only when it comes from `socket._fallback_socketpair`.

## D-35: A conversion must start from the unit its source is in; sentence numbers include `.99` and `5e1` (2026-10-18)

**Decision.** (1) L1 refuses a unit conversion whose starting unit is not the unit of its source (`wrong_conversion_source`, L1-021, repair route `retry_plan`). An unknown source unit fails closed. (2) The copy-number pattern in `api/verify/provenance.py` now reads a leading-dot decimal (`.99`) and an exponent (`5e1` is 50) as numbers; a digit run after a letter, digit, underscore or dot is still part of an identifier.

**Why.** Both came from the third kit-guardian round (2026-10-18). The agent was stopped by a safety classifier before it ran any page, so these two were not proven by an attack; each was a question about ordinary code, answered by reading it and by a data-level test with hand-built dicts. (1) `convert()` checks the factor for `from` to `to`, `_chain_unit` reports a conversion's unit as `to`, and L3 recomputes the same chain, so `convert(<metres>, "mm", "m")` passed every check while showing a value 1000 times too small, labelled metres; the existing test even applied an "mm" conversion to a control declared in newtons and expected no problem. (2) `.99 m` produced no number, so a Kit-owned sentence stating it was never compared with the backed values.

**Trade-offs / rejected.** Both fixes are in Python, so the Kit bundle (and its locked hash) is untouched and no stored Environment goes stale. The Kit's `convert()` still does not check at runtime; the verifier is the gate. Failing closed on an unknown source unit could refuse a legitimate page whose control has no unit; none of the 17 Environments is affected. **Not fixed, UNPROVEN:** three leads in `packages/kit/src/audit.ts` (list markers on elements other than `ol`/`ul`/`li`; text in `<head>` made visible; `script`/`style` text given a visible `display`) are recorded in `refdocs/evidence/2026-10-18-p1-guardian-round3.md` for a run with a person watching.

## D-36: Citations are pointers in the repository and quotations beside the local corpus; the Plan's citations decide the label (2026-10-18)

**Decision.** A Plan names citations by id (`citation_ids`). `data/citations/pointers.json` (committed, no textbook text) maps each id to a document, a PDF page, a short claim in our words, the topics and science models it supports, and who checked it. The quotation itself lives only in `<CORPUS_DIR>/citations.json`. `api/pipeline/grounding.py` resolves the ids through `api/evidence/registry.py`: only when the Plan names citations, a corpus is configured, and EVERY citation is found word for word on its page AND supports this Plan's topic or one of its models, the Environment is minted `kit-verified` with those citations; otherwise it is `model-checked` with an UNVERIFIED citation, and the trace says why. The live pipeline and `eval/environments/build.py` share the one function. The API loads the corpus once per process, not per request.

**Why.** Rule 13 forbids extracted passages in the repository, which is going public, and the owner has not confirmed public quotation (A-8). Pointers let a reviewer open the page and compare, without the text. The support check matters once a model plans: without it a planner could pick a valid but irrelevant id (a Hooke's law quotation on an osmosis page) and earn a label the page does not deserve. `evidence_for` used to reload and re-index the whole corpus on every request.

**Trade-offs / rejected.** The `kit-verified` labels reproduce only where the corpus exists (CI and cloud runs get `model-checked`, and `build.py` then refuses to overwrite the committed report). A Plan's `topic` or model must be listed on the pointer (a deliberate, reviewed list). The shown citation source is the raw document id and PDF page, not a book title and printed page; a friendlier display needs a wire-type change and was left. Rejected: committing the quotations (a public-quotation question the owner has not answered), fuzzy quotation matching (accepts a nearby wrong passage), and letting the planner write quotations. **Limit that stays (D-25):** a quotation proves the words are in the book, not that the Environment matches them; the label means "found and supported", not "a teacher agrees".

## D-37: The audit refuses every CSS route to a number with no text node, whether or not an attack was shown to work (2026-10-19)

**Decision.** `packages/kit/src/audit.ts` now lists as `forbidden` (and so the verifier refuses, `forbidden_markup`): (1) any stylesheet text or inline `style` attribute (on any element, the body, and every head element) that sets a counter (`counter-reset`, `counter-set`, `counter-increment`, `counter()`), styles `::marker`, gives a quoted `list-style-type` or `list-style`, or makes an element `display: list-item`; (2) marker content, a quoted marker string, or `display: list-item` on any element that is not an `li` (it was only looked for on `ol`, `ul` and `li`); (3) any non-visual element (`script`, `style`, `noscript`, `template`, `title`, `meta`, `link`, `base`, `head`), in the head or the body, whose computed `display` is not `none`. Kit 0.1.0 was relocked (D-29).

**Why.** The third `kit-guardian` round (2026-10-18) was stopped by a safety classifier before it ran any page, but its reading of the code named three places the audit does not look. None was shown to be exploitable: nobody built a page that minted. They are closed anyway because each is a way for a number to appear without a text node the audit reads, the fix is a stricter refusal with no known cost, and waiting for a proof of exploit is the wrong order for a verifier whose whole claim is that nothing unverified is shown. This is defence in depth, not a response to a demonstrated break.

**Trade-offs / rejected.** A page that legitimately uses CSS counters, a custom marker or a visible `<title>` is now refused; the 16 Environments and the Kit's own styles use none (all 16 still verify, L6 is unchanged at 56 of 61 with 0 of 12 false positives, hostile 20 of 20). Computed-style checks need a real browser: in the jsdom unit tests only the constructs jsdom computes are exercised, and the real guarantee is the Chromium harness. A page can still be rejected for an innocent inline `counter-*` it never uses visibly; that is the price of failing closed. **What this does NOT do:** it does not replace the supervised attack pass (`refdocs/guides/guardian_pass.md`), which also covers navigation, the gate and the plan path, and may find routes this list does not name.

## D-38: The web UI takes Synapse V3's design language, and not four of its behaviours (2026-10-22)

**Decision.** The V4 web shell is restyled on Synapse V3's design: its tokens (`Synapse-V3/frontend/app/globals.css`, `tailwind.config.ts`), fonts (Fredoka, Nunito, JetBrains Mono through `next/font`), the chunky pressed buttons, the top bar with the Axi mascot and a theme toggle, the "Today's flow" rail with Quick starts, the lab-bench pane, badges and the staged progress card. The sources of intent are `Synapse-V3/design/BRAND.md` and `design/FLOW.md`. Every ported file starts with a provenance comment (rule 5) and is re-expressed for Next 16, React 19 and Tailwind 4, not pasted. Four V3 behaviours are **not** ported: (1) "Watch the code being written", which streams unverified HTML to the student (hard constraint 1); the staged card is driven by V4's stage events and the Plan instead. (2) The "Not fully checked" draft view of an unverified page (constraint 1: V4 refuses, it does not show a draft). (3) `fitArtifactToFrame`, which edits the HTML after it was hashed; fitting moves into the Kit. (4) Saved labs as raw HTML in `localStorage`; a saved item is reopened through the delivery gate. V3's "Science checked" badge becomes a badge keyed to the Environment's real label (`kit-verified` or `model-checked`), and XP, streak and gem counters are not ported (invented numbers).

**Why.** The owner said the UI builds on the V3 design and style (2026-10-22). V3's look is documented and was designed phone-first. The four exclusions each break a hard constraint, so they are decided here once and not re-argued per component.

**Trade-offs / rejected.** The iframe has an opaque origin and cannot read the host's theme, so a theme toggle needs a Kit host-to-frame listener (a Kit behaviour change: relock under D-29, `kit-guardian` review). V3's 32 px toggle and the 44 px rule (constraint 10) conflict, so the toggle grows. Rejected: copying V3 files verbatim (different framework versions, and the constraint exclusions above); keeping V4's current plain styling (the owner asked for V3's look).

## D-39: Scope is the PRD end state plus every feature the demo video shows; Present mode is a presentation, not a teacher dashboard (2026-10-22)

**Decision.** "Complete" means the PRD end state (P3 to P8 and the deploy gate) and also the features the demo video shows that V4 does not yet have: the Amali lab report export (C2), the exam mirror (C3), Bahasa Melayu (C4), chapter packs (C5), a Present mode, and V3-style drag-and-drop benches rebuilt as Kit components. All content for them comes from V4's own Plans and cited models, never from wording invented for the video. **Present mode** is a full-screen Stage with a "Presenting" chip, for projecting one Environment to a class. It has no accounts, no class state, no student data and no teacher view, so it does not reopen the PRD non-goal on teacher dashboards. `ASSUMED:` the exact behaviour of Present mode (the chip was the video author's invention); confirm with the owner in the W6 plan before building.

**Why.** The owner chose "PRD end state + video" so the shown product becomes true. The audit found 18 shown items that were not built, partly built or built differently.

**Trade-offs / rejected.** More surface to verify and review: each new bench needs a Kit registration suite and a verifier that can drive drag gestures, and Bahasa Melayu ships only reviewed strings, so it depends on a human reviewer. Rejected: re-cutting the video to match the product (the owner wants the product to match the video); building teacher dashboards (still a non-goal).

## D-40: Paid runs are raised one at a time; the caps stay hard stops (2026-10-22)

**Decision.** `LLM_MONTHLY_CAP_USD` and `LLM_TOTAL_CAP_USD` stay enforced at the LLM seam and refuse a call before it is sent. The owner raises a cap by editing `.env` when a run needs more room; the assistant never edits `.env`. Every paid run still states a projection and a hard bound, runs the cost-auditor, and waits for the owner's typed amount (rule 7). The remaining-budget planning in `remaining_work.md` ("with a $2.00 all-time budget, $1.74 remains") is a status line, not a plan constraint.

**Why.** The owner chose "raise it later, per run" over a fixed $2 plan, because L4 adds a model call per Environment and the Free lane and the 24-question run need measuring.

**Trade-offs / rejected.** Without a fixed budget, no workstream can be sized in advance by cost, so each paid workstream (W8) has its own projection at the time. Rejected: planning around $2.00 (it would cut the L4 and Free measurements); removing the all-time cap (it is the only bound on a single operator with no auth, D-11).

---

## Working assumptions (`ASSUMED:`)

Not decisions: guesses made to keep moving. Each one must be confirmed or killed before anything load-bearing is built on it. When one is resolved, delete it here and write a real ADR above. The full numbered list (A-1 to A-18) lives in `refdocs/synapse-v4-PRD.md` section 8; the load-bearing ones:

1. **A-5 ASSUMED:** the oracle ladder, and that textbook worked examples can serve as an independent reference. Measured at P2.
2. **A-2 ASSUMED:** the Kit API shape and size guess. Replaced by the P0 census and P1 spikes.
3. **A-10 PARTLY CONFIRMED (P1 spike, 2026-10-16):** the harness verifies with no network under `unshare --net` at no measurable cost (`refdocs/evidence/2026-10-16-p1-isolation-spike.md`); `RLIMIT_AS` breaks Chromium, so memory needs a cgroup; a browser exploit is not covered. Still ASSUMED for the exploit case. The hosting option is the owner's at the deploy gate.
4. **A-11 ASSUMED:** the reading of "public students, no accounts" plus "single user, no auth". Needs the owner's confirmation.
5. **A-8 ASSUMED:** the corpus may be used locally and quoted briefly with citation. Unconfirmed legally.
6. **A-4 ASSUMED:** Compose lane cost is well below v3's about $0.19. Measured at P3.
7. **A-14:** the name "Synapse" collides with a published 2026 paper. Decide before a public URL.
8. **A-19 PARTLY CLOSED (D-31):** with `STORE_ATTESTATION_KEY` set the gate refuses unsigned or altered rows; without it the writers of the Environment store are still trusted. Required at the deploy gate. Originally: the writers of the Environment store are trusted. The gate re-hashes, re-scans and re-checks the CSP and Kit, but does not re-render and the row has no signature, so someone who can write the SQLite file can insert an Environment the verifier never saw. Acceptable only while the API is single-operator and not public (D-11). Close it (an HMAC attestation with a key outside the data directory, or re-rendering on delivery) at the P7 deploy gate. Pinned by `test_S3_KNOWN_GAP_*`.
9. **A-20 CONFIRMED by the owner (2026-10-16):** the "L6 planted-physics suite" (generation-time detection-rate measurement) and the per-micro-model registration suite required by hard constraint 6 are separate; both are built (`eval/l6`, `packages/kit/src/science/science.test.ts`).
