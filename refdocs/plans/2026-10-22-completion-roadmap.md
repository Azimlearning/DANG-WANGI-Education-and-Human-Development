# Plan: the completion roadmap (W0 to W11)

> The umbrella plan for finishing Synapse v4. Decisions: D-38, D-39, D-40. Execution doc: `refdocs/execution/2026-10-22-completion-roadmap.md`. Each workstream below gets its own plan and execution pair before any code is written for it (CLAUDE.md rule 2); this file fixes the order, the scope and the evidence each one must produce.

## Why this exists

On 2026-10-22 the owner asked for the rest of the development to be planned so it can be executed in order. Three inputs came together: the project's own docs (STATUS, `remaining_work.md`), an audit of the demo video against the code (18 shown items were not built, partly built, or built differently), and a priorities review. The owner then set the scope:

- "Complete" means the PRD end state (P3 to P8 and the deploy gate) **and** every feature the demo video shows, so the video becomes true.
- The web UI is built on Synapse V3's design and style (D-38).
- The L4 wording check and the Free lane are built together.
- Paid runs are raised one at a time (D-40).
- **Time is not a variable.** Work is ordered by dependency and correctness. The "cheapest route given a deadline" section of the old `remaining_work.md` is retired.

## What's already covered

Built and verified, so nobody rebuilds it: the trust engine (Kit, verifier L0 to L3 and L6, mint, gate, sandbox, store attestation), the Mark 3 pipeline on fakes and three small paid runs, 16 `kit-verified` Environments with 17 science models, the router and misconception matcher, the offline export and share links, device-local progress, the hint ladder, predict card, concept check and worked solution, and the experiment-card and table components. See `STATUS.md`.

## Findings from the code that shape the order

1. **STATUS had drifted** (Kit lock, test counts, P5 status). W0 fixes it.
2. **P5's exit criterion is not met.** The library lookup in `api/pipeline/run.py` runs after route and explain, both of which can cost money, and matches only the exact canonical question. There is no live Instantiate path.
3. **L4 has a clean hook.** `api/prompts/verifier_l4.v1.md` exists and nothing calls it. `verify_environment` (`api/verify/mint.py`) is synchronous and model-free and is used offline by `eval/l6` and `eval/environments`, so it stays model-free. L4 judges the Plan's sentences before assembly and passes its verdict into the verifier, which records `L4` in `checked.layers`.
4. **The Free lane fits the existing CSP** (`api/postprocess.py` allows `'unsafe-inline'` scripts and `/vendor/`). Only the route name `free_lane` exists in `api/pipeline/failchecks.py`.
5. **V3's UI is documented and portable** (`Synapse-V3/design/BRAND.md`, `design/FLOW.md`, `frontend/app/globals.css`, `tailwind.config.ts`, `frontend/components/`), but it is Next 14 and Tailwind 3 against V4's Next 16, React 19 and Tailwind 4. Four of its behaviours break hard constraints and are not ported (D-38).
6. **V3's four benches** (titration, Hooke's law, yeast fermentation, orbit) are raw HTML in Python strings with their own palettes. They can only become `kit-verified` as Kit components with cited models, and the verifier's L2 must learn to drive drag gestures.
7. **There is no i18n** and **no path from the table's recorded rows to the host**, which the Amali report and Bahasa Melayu both need.

## Scope

**In:** workstreams W0 to W11 below.

**Out, with reasons:**
- Student accounts, payments and teacher dashboards (PRD non-goals; D-11). Present mode is a presentation, not a dashboard (D-39).
- Streaming unverified output, XP and streak counters, and the other V3 exclusions (D-38).
- Widening to "any question". The narrow KSSM scope is what makes verification possible.
- Adopting the OpenUI packages (install-time telemetry; hard constraint 13; see the 2026-10-21 evidence note).
- Spaced repetition (an idea in the brainstorm, never scheduled).

## Approach: the workstreams, in dependency order

Marks: **(O)** needs the owner. **($)** is a paid run: cost-auditor first, projection, owner's typed amount.

| # | Workstream | Closes | Depends on |
|---|---|---|---|
| W0 | Ground truth: commit pending docs, fix STATUS drift, ADRs D-38 to D-40, this plan | doc debt | nothing |
| W1 | L4 wording check and the Free lane (labelled `model-checked`, never `canonical`, logged as a Kit gap) | P3 | W0 |
| W2 | Instant, free library hits: lookup before explain, topic-level Instantiate through the gate | P5 exit criterion | W0 |
| W3 | V3 UI port: tokens, fonts, chrome, staged card, honest badge, theme toggle (with a Kit listener), a11y sizes | UI | W0 |
| W4 | Interaction Kit and the V3 benches rebuilt; L2 drives drag gestures; two new cited models | video benches | W3 |
| W5 | Pedagogy: misconception follow-up (C1), Amali report with `record` (C2), exam mirror (C3) | P6 | W4 for C2 |
| W6 | Reach: Bahasa Melayu (C4), chapter packs and the bridge (C5), Present mode, friendly citations (B4) | P7 features | W3 |
| W7 | Content and evidence: OCR and catalogue (B1), misconception sources (B2), manifest citations (B3), constants table (B5), more models (B8) | P2, P4 | none |
| W8 | Paid measurements ($, O): 24-question run, L4 and Free canaries, prompt caching | A-4 | W1 |
| W9 | Trust, accessibility, CI: supervised guardian pass (O), real-browser keyboard, reduced-motion and screen-reader pass, real phone (O), CI | constraint 10, hard constraint 1 | W1, W4 |
| W10 | Deploy gate: per-session and per-day limits, isolated verification container, attestation key, Kit release, name, licence, host (O), corpus quotation (O) | P7 gate | all |
| W11 | People and the study (O): teacher review, blind router labels, BM review, learner study | P8, `reviewed` labels | any time |

W0 then W1 and W2; W3 can run beside them (the surfaces do not overlap); W4 after W3; W5, W6, W7 interleave; W8 after W1; W9's attack pass after W1 and W4 because the verifier changes; W10 last.

## Risks and unknowns

| Risk | Confidence | Mitigation |
|---|---|---|
| L4 (an LLM judging wording) misses false prose or flags correct prose | Unknown until measured. L6's `page-false-prose` row is one case, not a rate | Measure on a larger planted set with a fake responder first, then a small paid canary; report the miss rate |
| The drag-gesture verifier (W4) is the biggest new attack surface | Medium; the harness already presses real input (D-17) | `kit-guardian` on every Kit change; W9 attack pass after W4 |
| Rebuilding V3's benches as Kit components costs more than porting them | High that it is more work; that is the price of `kit-verified` | Build one bench end to end first (Hooke), then the rest |
| Bahasa Melayu depends on a human reviewer | High | Ship the mechanism and the review workflow; only reviewed strings render |
| Tailwind 4, Next 16 and React 19 differ from the V3 code and from memory | High | Read current docs before writing (rule 6) |
| `kit-verified` is not a teacher's review (D-36) | Known | W11 |
| The V3 repo state at port time is not pinned in this repo | Known | Each W3 file records the V3 repo, path and commit (rule 5); the badge history is in V3 commits `410d7a3` and `db39e8e` |

## Definition of done

The project is complete when all of these are observable:

- Every row of the STATUS phase table is ✅ with a ledger row that names the command and result.
- The L4 check refuses `page-false-prose` in the L6 run with no new false positive, the hostile set is 20 of 20, and a Free fixture mints only as `model-checked`.
- A covered topic opens with no model call (spy-provider test) and in under one second locally.
- The web UI follows V3's design, passes the smoke at 360 px with 44 px targets, and shows no unverified output at any point.
- Each feature the video shows exists and is verified in Chromium: a lab report from recorded rows, an exam-mirror answer scored "X of Y marks", an EN/BM switch showing only reviewed strings, a chapter pack that opens offline, Present mode, and drag-and-drop benches.
- A supervised attack pass is on record, and the deploy-gate checklist is ticked item by item in the changelog.
- No text in the repo, the UI or the video claims more than the evidence supports.
