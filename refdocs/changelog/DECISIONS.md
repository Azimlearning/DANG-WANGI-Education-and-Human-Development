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

---

## Working assumptions (`ASSUMED:`)

Not decisions: guesses made to keep moving. Each one must be confirmed or killed before anything load-bearing is built on it. When one is resolved, delete it here and write a real ADR above. The full numbered list (A-1 to A-18) lives in `refdocs/synapse-v4-PRD.md` section 8; the load-bearing ones:

1. **A-5 ASSUMED:** the oracle ladder, and that textbook worked examples can serve as an independent reference. Measured at P2.
2. **A-2 ASSUMED:** the Kit API shape and size guess. Replaced by the P0 census and P1 spikes.
3. **A-10 ASSUMED:** headless Chromium in a no-network container is adequate isolation for a public deploy. P1 spike.
4. **A-11 ASSUMED:** the reading of "public students, no accounts" plus "single user, no auth". Needs the owner's confirmation.
5. **A-8 ASSUMED:** the corpus may be used locally and quoted briefly with citation. Unconfirmed legally.
6. **A-4 ASSUMED:** Compose lane cost is well below v3's about $0.19. Measured at P3.
7. **A-14:** the name "Synapse" collides with a published 2026 paper. Decide before a public URL.
