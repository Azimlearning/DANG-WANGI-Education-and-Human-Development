# Plan: P2, P5 and P6 cloud scope (evidence, library and lifecycle, pedagogy)

> PRD section 6 phases P2, P5, P6; decisions D-21, D-25, D-27. Execution doc: `refdocs/execution/2026-10-16-p2-p5-p6-evidence-library-pedagogy.md`. **Written after the build** (a CLAUDE.md rule 2 deviation, logged in the changelog).

## Why this exists

The owner asked to finish as much as possible in the cloud. P2 (evidence), P5 (library, lifecycle) and P6 (pedagogy) each have a part that needs nothing but code and fakes. The textbook corpus itself cannot be here (rule 13, A-8), so P2 is built against a synthetic corpus and a local ingestion path.

## Scope

**In:**
- **P2**: a corpus format (jsonl per document, never committed), BM25 retrieval, exact-after-normalisation quotation verification, the `Evidence` protocol used by mint and gate, an ingestion tool for local use, and an experiment catalogue (metadata only, no textbook text).
- **P5**: canonical-question cache, `withdraw`/`restore`/`flag`, library listing, stale-by-Kit-hash, endpoints, and the pipeline's library-hit path.
- **P6**: four pedagogy components (`hintLadder`, `conceptCheck`, `predictCard`, `workedSolution`), Plan fields, plan checks, assembler slots, and enriched golden plans.
- **LLM seam hardening** from the cost audit: typed `ProviderFailure.kind`, `ProviderRejected`, conservative booking of timeouts and cancels, `ensure_budget`, live-mode prerequisites.

**Out:** loading real textbook text (local, A-8); a live provider (needs the owner's confirmed amount); spaced repetition, accounts, analytics (later).

## Definition of done

- A synthetic-corpus test shows `kit-verified` minted only when every quotation is found, refused otherwise, and refused again at the gate if the corpus changes.
- A repeated question is served from the library through the gate; a withdrawn or stale row is not.
- Six golden plans carry predict, hints, concept check or worked solution and still mint.
