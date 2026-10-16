# Plan: P0 Walking skeleton and coverage census

> Phase P0 of `refdocs/synapse-v4-PRD.md` section 6. Execution doc: `refdocs/execution/2026-10-16-p0-walking-skeleton-census.md`.
> A plan says **what and why**. The execution doc says **how and in what order**. Keep them separate: when they merge, both stop being read.

## Why this exists

Every later phase assumes one Environment can travel the whole trust path: be produced, scanned, rendered under a harness, minted by the verifier only, stored, re-gated on delivery, and shown to a student inside an exact sandbox. v3 proved the raw-HTML half. Arcana v2 proved the mint, store and gate half. Nobody has joined them in one repo, and nothing has been measured about what the Kit must contain: its size and API are guesses (A-2) and the first vertical is undecided (D-09).

P0 builds the thinnest end-to-end slice on fakes, and produces the one free measurement that orders everything after it: a census of the 53 KSSM topics against the Kit's micro-component kinds.

## What's already covered (no work needed)

Pieces that exist and are ported with provenance (CLAUDE.md rule 5). Each is read in full first and adapted, never pasted and patched until it compiles.

| Need | Source | Commit or date |
|---|---|---|
| Wire schema, codegen to strict Pydantic, drift check | Arcana v2 `packages/schema` and `packages/schema/codegen/to_python.ts` | `21c6dcf5` |
| LLM seam, spend ledger, cap before send | Arcana v2 `api/llm/service.py`, `ledger.py`, `pricing.py` | `21c6dcf5` |
| Mint closure and the "only the verifier mints" test | Arcana v2 `api/labs/verifier.py` | `21c6dcf5` |
| Delivery gate that re-derives and re-hashes | Arcana v2 `api/genui/validate.py` pattern, `web/lib/labFrame.ts` | `21c6dcf5` |
| Forbidden-API scan, CSP injection, single document, size cap | Synapse v3 `backend/postprocess.py` | v3 as of 2026-08 |
| Render harness assertions (ready, control wiring, no errors) | Synapse v3 `evals/render_check.py` and `docs/EVALS.md` section 4 | v3 as of 2026-08 |
| Bridge protocol names (`synapse_ready`, `synapse_event`, `synapse_error`) | Synapse v3 generator prompt v8, Block C | 2026-07-18 |
| The 53-topic taxonomy with source-page citations | Synapse v3 `ml/router-distill/kssm_topics.py` v3 | 2026-07-18 |

## Scope

**In:**
1. Workspace and toolchain (uv project, pnpm workspace, `api`, `web`, `packages/schema`, `packages/kit`).
2. Wire schema and codegen with a drift check.
3. Settings, a deterministic fake LLM, the spend ledger and cap; live mode refuses to start without a key and a cap.
4. Kit v0: observable, `environment`, `slider`, `readout`, bridge, one tiny science micro-model, esbuild bundle, manifest.
5. One hand-written reference Environment composed over Kit v0 (an illustration; **not** the first vertical).
6. Verification v0: L0 scan, Playwright render harness, mint, store, gate.
7. API `/ask` on fakes streaming `meta`, `text_delta`, `environment`, `done`.
8. Web shell: stream, hash check, `sandbox="allow-scripts"` iframe, Peek and Stage.
9. The coverage census of the 53 topics.

**Out (and why):**
- **A live LLM, the planner, router, prompt packs:** P3, and D-08 requires the owner's confirmation for paid runs.
- **L1 provenance, L3 cross-check, L6 planted-physics suite:** P1. P0 only has the layers that need no Kit contract.
- **Corpus, retrieval, citations:** P2 and D-14. The P0 science micro-model's citation field is explicitly `UNVERIFIED`.
- **The library lifecycle, multiple kits, accelerators:** P4 and P5.
- **Bahasa Melayu, offline file, deploy:** P7.
- **A trust label of `kit-verified`:** unreachable until L1 and L3 exist. P0 uses a P0-only label `dev-fixture`, removed in P1.

## Approach

Order is by seam. The wire type is the load-bearing seam between API and web, so it comes first (task 2). The Kit manifest is the second seam, between the Kit and the API, so it follows the Kit (task 4). The trust path (task 6) is built before any model could feed it, so that every later phase plugs into a gate that already refuses things.

Everything runs on the fake LLM. The reference Environment is written by hand so that the verification path is exercised with a known-good input and with deliberately broken variants, which is how the planted-defect habit starts.

The census (task 9) is a judgement exercise over a taxonomy, not a measurement. It states its criteria, marks confidence per row, and the owner reviews it. Its outputs are estimates that order P1 and P4; none of them is a coverage claim.

## Risks & unknowns

Be honest about confidence. "I have read this library's docs" and "I think this library does that" are different rows, and only one of them is safe to build on.

| Risk / unknown | Confidence | Mitigation |
|---|---|---|
| Ported code assumes different library versions or a different layout | Medium: the files were read, never run in this repo | Read fully, tests first, rule 5 and rule 6 |
| Playwright install adds a large browser download on a 94 percent full disk (17 GB free) | Medium | Check free space first, install Chromium only, record the size |
| Python Playwright is not installed here today | High (observed) | Task 6 installs it and records versions |
| The Kit observable API turns out clumsy for a model to write | Low in P0, higher later | P0 keeps the API tiny; P1 and P3 test it with a real model under confirmation; the API is A-2 |
| Next.js, Tailwind and pnpm 10 differ from Arcana v2's Next 16.3.8, pnpm 9.12 | Medium | Read current docs (rule 6), do not copy config from memory |
| A `srcdoc` iframe resolves relative URLs against the parent, so `/vendor/kit/` must be same-origin with the page | High (a v3 finding) | A rewrite in the Next config proxies `/vendor/*` to the API, verified by the browser smoke |
| Census rows are subjective | High that they are | Criteria written first, confidence per row, owner review, labelled estimates |
| The reference Environment is mistaken for the first vertical | Medium | Named `reference-*`, labelled `dev-fixture`, D-09 and the plan say so |

## Definition of done

This phase is done when every line below is true and has been *observed*, not assumed:

- From a clean checkout, `uv sync` and `pnpm install` succeed and `uv run pytest` and `pnpm -r test` pass; the counts are recorded in STATUS.
- `pnpm codegen:check` is clean, and a deliberate un-regenerated schema change makes it fail.
- With no key set, the API starts in fake mode and makes no network call (a test proves it). In live mode, a missing key or cap stops startup naming the variable. A request that would exceed the cap is refused before any provider call.
- `POST /ask` on fakes streams `meta`, `text_delta`, `environment`, `done` in that order.
- In a real browser the Environment renders in an iframe whose `sandbox` attribute is exactly `allow-scripts`; moving the slider changes the readout; a `fetch` from inside the frame is blocked; there are no console errors.
- A planted forbidden-API Environment is refused at L0 by name; a planted dead-control Environment is refused at the render layer naming the control; a one-byte tamper of a stored Environment is refused by the gate; a test proves `VerifiedEnvironment` cannot be constructed outside the verifier.
- The census has 53 rows, defined columns, per-subject and per-model-kind counts, and an owner review recorded.
- STATUS has a verification ledger row, with a real command and result, for each line above.
