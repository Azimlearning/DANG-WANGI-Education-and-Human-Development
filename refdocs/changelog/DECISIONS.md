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
9. **A-20 ASSUMED:** the plan's out-of-scope "L6 planted-physics suite (P1)" is the generation-time detection-rate measurement; hard constraint 6's per-micro-model registration suite is a separate requirement, and it was built for `hookes` in P0. Confirm with the owner.
