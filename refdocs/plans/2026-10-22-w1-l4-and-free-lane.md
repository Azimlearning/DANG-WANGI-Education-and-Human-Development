# Plan: W1, the L4 wording check and the Free lane

> Workstream W1 of `refdocs/plans/2026-10-22-completion-roadmap.md`. Decisions: D-41 (this work), D-07 (Free lane policy), D-21 and D-25 (labels). Execution doc: `refdocs/execution/2026-10-22-w1-l4-and-free-lane.md`. Closes the unbuilt parts of P3.

## Why this exists

Two pieces of the PRD's pipeline were never built:

1. **L4, the wording check.** The verifier proves where numbers come from, but nothing reads the words. The L6 baseline has a known miss, `page-false-prose`: the note "extension is inversely proportional to the load" passes every layer because it contains no number. The prompt pack `api/prompts/verifier_l4.v1.md` exists and nothing calls it. A model-composed UI makes this hole matter more, because wrong science hides in prose.
2. **The Free lane.** The PRD has three lanes. A question the Kit cannot express (an assembly gap, or a Plan the planner cannot get past the checks) currently gets the written answer only. The verifier already branches on `lane == "free"` in five places, but nothing produces a Free Environment, and a Kit-less page cannot even pass the render harness (see Findings).

The owner decided (2026-10-22) that both are built together.

## What's already covered

- `verify_environment` already accepts `lane="free"`: it skips the Kit-lane scan and the L1 and L3 layers and never grants `kit-verified` (`api/verify/mint.py`, `guard_label`, test `test_free_lane_can_never_be_kit_verified`).
- The delivery gate (`api/verify/gate.py`) and the store handle any lane; the offline export already describes the Free lane in words (`api/export.py`).
- The pack `verifier_l4.v1.md`, the fail-check route name `free_lane`, and a lane text for Free in the web Provenance card.
- Layer names and stage names are open strings on the wire, so no schema change is needed for either.

## Findings that shape the design

1. **A Kit-less page cannot pass the harness today.** L0 forbids `postMessage` and `window.parent` (`api/verify/scan.py`), and the harness waits for a `synapse_ready` message (`api/verify/render.py`, `HARNESS`). The web host does not wait for it (`web/components/EnvironmentFrame.tsx`). So for the Free lane the harness will treat the iframe's `load` event as ready. That is a verifier change (kit-guardian review). The Free page still has to meet the rest of the harness contract: declared controls that change declared readouts, accessible names, 44 px targets, no overflow at 360 px, reduced motion, a document language.
2. **L4 must stay out of `verify_environment`.** That function is synchronous and model-free and is used offline by `eval/l6` and `eval/environments`. L4 runs in the pipeline; the mint is told, by a flag, whether a wording check passed, and claims the layer `wording` only then.
3. **A fake judge must never be claimed as a check.** Fake mode runs no L4 (`Deps.wording_check` is off by default and turned on only in live mode), so fake runs never show a "wording" layer.
4. **The existing L4 pack says "You do not check numbers; code already did."** That is false for a Free page. The Free lane needs its own pack that also checks the numbers and formulas in the page.
5. **The textbook quotation must not be sent to a paid API.** The pack has a `passage` input. This plan passes the pointer's `claim` (our own words, committed in `data/citations/pointers.json`), never the corpus quotation (A-8, rule 13).
6. **No question text is logged for gaps.** Traces store only a hash of the question. The gap log keeps the hash, the routed topic, domain and pattern, and the reason (`assembly_gap:<part>` or the plan check codes), which is what a Kit backlog needs.

## Scope

**In:**
- L4 for Compose: judge a Plan's prose before assembly, inside the plan retry loop (issues go back to the planner once, like plan checks).
- The Free lane: a generator pack, a reply parser, verification as `lane="free"` with label `model-checked` and the UNCHECKED citation, an L4 pass over the page's visible text (required: it is the only content check Free has), storage and delivery through the gate, the gap log, a setting that turns it on (default off).
- The harness change for Free pages (ready on load).
- Honest wording on the wire: a Free-specific `limits` sentence from the gate, and `wording` added to the web's layer text.
- A fixed protocol for measuring L4 before any paid run: planted false and true wording cases and a scorer (hard constraint 9).

**Out, with reasons:**
- Paid runs. L4 and Free canaries are W8 and need the owner's amount.
- Making L6 count a model judge. L6 is the model-free verifier's detection rate; a stub judge would inflate it. `page-false-prose` stays a known miss of the model-free layers and is covered by L4 in the pipeline; the real detection rate is measured in W8.
- Letting a model-written Plan earn `kit-verified` (A8) and the Free lane in the offline gallery.
- Streaming a Free page before it is verified (hard constraint 1).

## Approach

- `api/pipeline/wording.py`: the texts of a Plan (`plan_texts`), the visible text of a Free page (`page_texts`), the verdict parser (strict JSON, fail closed on malformed replies).
- Prompts: `prompts.wording_request` (existing pack v1), `prompts.free_request` and `prompts.free_wording_request` (new packs `free.v1.md` and `verifier_l4_free.v1.md`).
- `run.py`: wording inside the plan loop; Free fallback on `AssemblyGap` and on plan failure; `MAX_LLM_CALLS` 6 to 8; `Deps.wording_check`, `Deps.free_lane`, `Deps.gap_log_path`.
- `mint.py`: `verify_environment(..., wording_checked=False)`; `_layers` adds `wording`.
- `render.py`: `render_check(..., kit_lane=False)` marks the page ready when the iframe loads.
- `gate.py`: lane-aware `limits`.
- Settings: `FREE_LANE_ENABLED` (default false) and documentation in `env_setup.md`.
- Fail-check registry: `L4-001` (wording refused, `retry_plan`) and `FREE-001` (the reply was not a single HTML document), tied to the code by the existing registry test.
- Fakes: a deterministic wording responder (ok unless the text carries a test marker) and a Free responder returning a hand-written compliant page, so the whole Free path is exercised in real Chromium with no key.

## Risks and unknowns

| Risk | Confidence | Mitigation |
|---|---|---|
| An LLM judge misses false prose or flags correct prose | Unknown; one L6 row is not a rate | The planted-case protocol is fixed first; the paid measurement is W8; the layer is described as "read by a second model", never as a proof |
| Free pages are the largest unverified surface (arbitrary model JavaScript with no Kit lockdown) | High that the risk is real | Off by default; L0 scan, real-browser run with controls, CSP `connect-src 'none'`, the exact sandbox; label `model-checked` plus a Free-specific limits line; `kit-guardian` on the harness change; the W9 attack pass covers it |
| The ready-on-load change weakens the harness | Low to medium | Only for `kit_lane=False`; a page cannot forge host-driven readiness; navigation still counts as a refusal; tested with a navigating Free page |
| A model reply for Free will often fail the harness contract (declared controls, names, 44 px) | High | The pack states the contract exactly; one retry is not built (budget); a failure degrades to the written answer. The paid canary in W8 measures the rate |
| More paid calls per request | Known | `MAX_LLM_CALLS` 8; cost-auditor review before the change; the cost projection is regenerated |
| `window.__synapse.ready` on load fires before the page script runs its setup | Medium | Wait for `load` then two animation frames, the same timing as the Kit's own ready |

> **Update 2026-10-23.** The first build was reviewed by `kit-guardian` and `cost-auditor` and changed (D-41, amendment): a page with a fill does not claim `wording`; an unreadable page is refused; Free pages get their own scan and no verify flag; judge packs are fenced and the Free judge sees the topic, not the question; an L4 refusal does not fall to Free; a Free page is not paid for unless its reading also fits. The text above is the original plan; the ADR is the record of what was built.

## Definition of done

- A Compose run on a stub judge that flags a planted false sentence retries the planner once with the L4 issues, and then degrades; with a judge that passes, the stored Environment's `checked.layers` includes `wording`, and a fake-mode run never includes it.
- With `FREE_LANE_ENABLED` on and a question whose assembly has a gap, the pipeline delivers a Free Environment: lane `free`, label `model-checked`, an UNVERIFIED citation, a Free-specific limits line, verified in real Chromium, stored, and delivered through the gate; a gap record is appended without the question text.
- A Free page that calls `fetch`, navigates, has an unnamed control, or whose control changes no readout is refused, each at its named rule.
- The Free path cannot mint `kit-verified` or `canonical`, and refuses when the wording judge is missing or says no.
- `eval/l6/run.py` still reports 56 of 61 refused with 0 of 12 false positives and the hostile set 20 of 20; the planted wording cases and their scorer exist and pass on the stub.
- The full test suites, lint, types and `pnpm codegen:check` are green; `kit-guardian` and `cost-auditor` have reviewed the diff and their findings are answered.
