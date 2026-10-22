# Where the project stands and everything that is left (2026-10-19)

> Written for the owner, who asked "how complete is this at hackathon level, and what is still pending". The percentages are the author's judgement with the arithmetic shown, not measurements. Update this file when a row changes, and keep `STATUS.md` (the phase table and known gaps) as the authority on facts.
>
> **Updated 2026-10-22.** The owner widened the target (D-39): the PRD end state plus every feature the demo video shows, with time not a variable (D-40 covers money). The percentages below were measured against the older, smaller "hackathon-level" definition and have not been re-estimated; do not read them as progress against the new target. The ordered plan is `refdocs/plans/2026-10-22-completion-roadmap.md` (workstreams W0 to W11); the last section of this file maps every item here to a workstream. The old "cheapest route to a demo" section was retired because it was built around a deadline.

## Why there is still work after "cloud is done"

The cloud session built everything that needs no real key, no textbook and no human: the Kit, the verifier, the pipeline, the store and gate, the web shell, on deterministic fakes. What was left falls into three kinds, and none of it could have been done there:

1. **Needs real data or money.** The live model, the textbooks. (Done in part on 2026-10-18: the corpus, 16 citations-checked Environments, three paid runs for $0.26.)
2. **Features that were never built** because the PRD schedules them for P6 and P7 (misconception follow-up, Amali mode, Bahasa Melayu, chapter packs, deployment). They were not blocked; they were next.
3. **Decisions and reviews only a person can make** (the name, the licence, hosting, a teacher's review, a real phone).

## How complete, and how that number was reached

"Hackathon-level production" here means: a judge can open a link, type a KSSM science question and get a verified interactive Environment with its source visible, on a phone, within about half a minute, with a number or two that back it up, and nothing about it can run up a bill or show an unverified page.

| Part | Weight | Done | Why that figure | Contribution |
|---|---|---|---|---|
| Trust engine (Kit, verifier, gate, sandbox) | 25 | 90% | Built and tested (655 tests, 56 of 61 planted bugs caught, 20 of 20 hostile). Three open leads and a supervised attack pass remain | 22.5 |
| Verified content | 15 | 60% | 16 Environments, all citations proved against the real textbooks; 30% of the 53 topics; no teacher review yet | 9.0 |
| Live question to Environment | 15 | 50% | Works 3 of 3 on three topics after one real defect was found and fixed; the 24-question set is unmeasured; the Free lane and the wording check are not built | 7.5 |
| Student experience | 15 | 70% | Chat shell, Peek and Stage, hints, predict, concept check, progress, share and offline file are built; no real-phone, screen-reader or keyboard pass; no Bahasa Melayu, Amali mode or misconception follow-up | 10.5 |
| Safe to put in front of strangers | 15 | 10% | Nothing is deployed. Limits are per address per minute only; no isolation container; no host, name or licence; the Kit is unreleased | 1.5 |
| Numbers and story for judges | 10 | 40% | Verifier detection rate, cost per Environment and the verified count exist; no learner result | 4.0 |
| Docs and process | 5 | 95% | Changelog, ADRs, STATUS, evidence notes | 4.75 |
| **Total** | 100 | | | **about 60%** (reasonable range 55 to 65) |

For comparison, by the PRD's own phases (P0 to P8 weighted equally: 100, 90, 90, 85, 70, 55, 85, 45, 35, 0) the project is about **65% complete**. The two numbers differ because the unfinished part is concentrated in the things a visitor sees and in deployment.

## Everything that is pending

Effort: S under an hour of work, M a few hours, L a day or more. "You" means it needs you; "Free" means no API money.

### A. Needs you (decisions, people, devices)

| # | Task | Why it matters | Cost | Effort |
|---|---|---|---|---|
| A1 | ~~Finish `.env`~~ Done by the owner 2026-10-19 (`CORPUS_DIR` real, caps 2.00 and 2.00) | | Free | Done |
| A2 | Paste the nine settings into `.env.example` (STATUS lists them) | Every other setting is documented there; the file is blocked to my tools | Free | S |
| A3 | Supervised verifier attack pass, `guardian_pass.md` | The only unmet Step 4 item; protects the core promise | Free | M |
| A4 | Say whether short textbook quotations may be shown publicly (A-8), or only cited page references | The provenance panel and the offline file show a short quotation | Free | S |
| A5 | Pick the name ("Synapse" collides with a 2026 paper, A-14), a licence, and where it is hosted | Without them there is no public URL | Free to $ (hosting) | S |
| A6 | A teacher or KSSM student checks the 16 Environments, the router labels (200 blind) and the five misconceptions | Nothing above `kit-verified` is possible without a person (hard constraint 3) | Free | M |
| A7 | Open a shared link on a real phone; one screen-reader pass; one keyboard-only pass | Accessibility is only checked statically and in a harness so far | Free | M |
| A8 | Decide whether a model-written Plan may earn `kit-verified` through retrieved citations | Today it cannot: the planner is not told the citation ids. A citation proves the topic is in the book, not that the model's wording is right | Free | S |
| A9 | ~~Decide the Free lane and the L4 wording check~~ Decided 2026-10-22: build both together (W1) | The PRD describes three lanes; two are built | Free | Done |
| A10 | Approve the learner study design and any participants (P8) | The "normalised gain" result is a PRD end-state target | Free | L |

### B. Free engineering I can do now

| # | Task | Why it matters | Effort |
|---|---|---|---|
| B1 | OCR the five Chemistry experiment scans (159 pages) and match the experiment catalogue | The PRD wants one record per KSSM practical; every entry says `confirmed_by_person: false` | M |
| B2 | Check the five misconception citations (`source_verified` is false) | Needed before the follow-up feature relies on them | S |
| B3 | Kit manifest and spec `citation` fields still say UNVERIFIED; remove or flag the `biology.cardiac_output` model (no textbook states it) | Hard constraint 6; relocks the Kit | M |
| B4 | Show a book title and printed page instead of the file id and PDF page in the citation | A student currently sees `textbook-physics-physics-f5-removed`, page 36; needs a wire-type change | M |
| B5 | A small table of well-known constants (g = 9.81 and so on) checked by the plan checks | The live planner chose g = 10 where the book uses 9.81 | S |
| B6 | Teach the ledger cache prices and turn prompt caching on | About 5,000 of the 9,000 input tokens of every plan call are the same each time; could cut the plan cost by roughly a third to a half. Needs a measurement | M |
| B7 | ~~Harden `audit.ts` for the three open leads~~ Done 2026-10-19 (D-37); the supervised pass is still needed for the other three scopes | | Done |
| B8 | More science models and Environments by measured gap (half-life, parallel resistance, refraction, logistic growth, molarity, percentage yield) | 16 of 53 topics today; each needs a textbook citation, a hand-written reference and planted-bug tests | L each batch |
| B9 | Continuous integration (tests on every push, and the smoke on Linux) | The Linux path of the smoke has never run since it was adapted; there is no CI | M |
| B10 | Router retrain on more data and an embedding comparison | Only if data beyond the v3 set exists; the measured spot check suggests the topic gate is permissive | M, skip unless data appears |

### C. Product features not built yet (each needs a plan and an execution doc first)

| # | Feature | PRD phase | Effort |
|---|---|---|---|
| C1 | Misconception follow-up end to end for three flagship misconceptions (probe, correction, check). The PRD's P6 success bar. The matcher is only a topic detector, so it should offer a probe, not a correction | P6 | L |
| C2 | Amali mode scaffold: problem, hypothesis, variables, procedure, a results table the student fills, a report skeleton on export | P6 | L |
| C3 | Exam mirror and challenge levels (design first; no design exists) | P6 | L |
| C4 | Bahasa Melayu for reviewed Environments: the translation mechanism and a review workflow; only reviewed strings ship | P7 | L |
| C5 | Chapter packs (several Environments in one offline file) and the MCP-Apps-shaped bridge | P7 | M to L |
| C6 | Per-session and per-day limits; the same limits at the proxy; verification in a no-network container with memory limits; a Kit release (bump 0.1.0 and make files immutable) | P7, deploy gate | L |

### D. Paid measurements (the only part that spends API money)

| # | Measurement | Expected cost | Why |
|---|---|---|---|
| D1 | The golden set without the exemplar, as many questions as the budget allows | About $0.027 per question when plans pass at the first attempt: 12 questions about $0.35, all 24 about $0.70, up to about $1.30 if every plan needs a retry | A real pass rate for the planner, which is the headline number for P3 |
| D2 | The cost of a prompt-caching change (after B6) | About $0.10 | Whether the saving is real |

Spent so far: **$0.26** (as of 2026-10-19; read `GET /spend` or the ledger for the current figure). The all-time cap in `.env` was $2.00 at that date. Caps are hard stops that the owner raises one run at a time (D-40); this is a status line, not a plan constraint.

### E. Evidence and study (P8)

| # | Task | Effort |
|---|---|---|
| E1 | Learner study design and the paper-ready evaluations (normalised gain, whatever it shows); model-judged scores are never the primary metric | L |

## Added 2026-10-22: found by reading the code and the demo video

| # | Item | Why it is pending | Workstream |
|---|---|---|---|
| F1 | The library lookup runs after route and explain, and matches only the exact question | The PRD's P5 exit criterion ("a covered topic opens in under one second with no model call") is not met; no live Instantiate path | W2 |
| F2 | The web UI is not built on Synapse V3's design (tokens, fonts, rail, Quick starts, bench pane, badges, Axi, theme toggle) | The owner's decision (D-38); four V3 behaviours are deliberately not ported | W3 |
| F3 | V3's four benches (drag masses, titration with stopcock and eye level, yeast tubes with a dial, orbit) have no V4 equivalent | The demo video shows them; they must be rebuilt as Kit components with cited models and a verifier that drives drags | W4 |
| F4 | No path carries the results table's recorded rows to the host; `resultsTable` and `record` do not exist | The Amali lab report (C2) needs both | W5 |
| F5 | No string tables anywhere (Kit and web strings are hard-coded English) | Bahasa Melayu (C4) needs a mechanism and a reviewer before any translated string ships | W6 |
| F6 | Present mode (the video's "Presenting to the class" chip) has no design | D-39: a presentation of Stage, no class state; behaviour is `ASSUMED` until the owner confirms | W6 |
| F7 | STATUS and the PRD decision log lagged the code (Kit lock, test counts, P5, D-34 to D-37) | Fixed 2026-10-22 | W0 (done) |

## Where each pending item is scheduled

The order is by dependency (see the plan for the reasons). W0 is done.

| Workstream | Items from this file |
|---|---|
| W0 Ground truth and decisions | F7, A9 (decided) |
| W1 L4 wording check and the Free lane | A9; the L4 gap in the verifier |
| W2 Instant, free library hits | F1 |
| W3 V3 UI port | F2; A2 can be done any time |
| W4 Interaction Kit and benches | F3; B8 (new models for the benches) |
| W5 Pedagogy | C1, C2 (with F4), C3 |
| W6 Reach | C4 (with F5), C5, F6, B4 |
| W7 Content and evidence | B1, B2, B3, B5, B8 |
| W8 Paid measurements | D1, D2, B6, and the L4 and Free canaries |
| W9 Trust, accessibility, CI | A3, A7, B9 |
| W10 Deploy gate | A4, A5, C6 |
| W11 People and the study | A6, A8 (decision), A10, E1 |

A8 (may a model-written Plan earn `kit-verified` through retrieved citations) is the owner's call and stays open until W11 or earlier; it does not block any workstream above.
