# Where the project stands and everything that is left (2026-10-19; rows updated 2026-10-25)

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
| B3 | ~~Kit manifest and spec `citation` fields still say UNVERIFIED; flag the `biology.cardiac_output` model~~ Done 2026-10-27 (D-58): honest text, cardiac output stays with a plain `useWhen` | | |
| B4 | ~~Show a book title and printed page instead of the file id and PDF page in the citation~~ Done 2026-10-25 (D-47): a book title and a PDF page, derived from the id; the printed page is not recorded | | Done |
| B5 | ~~A small table of well-known constants (g = 9.81 and so on) checked by the plan checks~~ Done 2026-10-25 (D-47): PLAN-020 | | Done |
| B6 | Prompt caching: ledger side done 2026-10-27 (D-55, `PROMPT_CACHING` off by default). Turning it on waits for one measured run | About 5,000 of the 9,000 input tokens of every plan call are the same each time; could cut the plan cost by a third to a half | M |
| B7 | ~~Harden `audit.ts` for the three open leads~~ Done 2026-10-19 (D-37); the supervised pass is still needed for the other three scopes | | Done |
| B8 | More science models and Environments by measured gap. Done 2026-10-27 (D-57, D-61): refraction, critical angle, specific heat, transformer, half-life, relative atomic mass, food energy, Boyle's law, parallel resistance, buoyant force, cell voltage, population density, electrical energy (22 of 53 topics). Left: logistic growth, molarity, percentage yield, the quadrat coverage percentage (needs an input-to-parameter relation) | Each needs a textbook citation, a hand-written reference and planted-bug tests | L each batch |
| B9 | ~~Continuous integration (tests on every push, and the smoke on Linux)~~ Written 2026-10-25 (D-47): `.github/workflows/ci.yml`; the first run on GitHub has not happened | | Partly |
| B10 | Router retrain on more data and an embedding comparison | Only if data beyond the v3 set exists; the measured spot check suggests the topic gate is permissive | M, skip unless data appears |

### C. Product features not built yet (each needs a plan and an execution doc first)

| # | Feature | PRD phase | Effort |
|---|---|---|---|
| C1 | ~~Misconception follow-up end to end for three flagship misconceptions (probe, correction, check). The PRD's P6 success bar. The matcher is only a topic detector, so it should offer a probe, not a correction~~ Built 2026-10-25 (D-48) for all five listed misconceptions as a probe; no adaptive follow-up | | Done |
| C2 | ~~Amali mode scaffold: problem, hypothesis, variables, procedure, a results table the student fills, a report skeleton on export~~ Built 2026-10-25 (D-49): lab report from recorded rows in Stage, text export | | Done |
| C3 | ~~Exam mirror and challenge levels (design first; no design exists)~~ Built 2026-10-25 (D-50): six items, keyword marking in the browser | | Done |
| C4 | ~~Bahasa Melayu for reviewed Environments: the translation mechanism and a review workflow; only reviewed strings ship~~ Built 2026-10-27 (D-62) as drafts: 30 translated Environments, the page strings, the EN/BM switch, the review tools. **Nothing is public until a fluent reviewer approves it** | P7 | Done, review open |
| C5 | ~~Chapter packs (several Environments in one offline file) and the MCP-Apps-shaped bridge~~ Chapter packs built 2026-10-25 (D-51); the MCP-Apps-shaped bridge is not | | Partly |
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

## Added 2026-10-27: the demo-video spec (`brag-output-2026-10-21-195546/v4-video-feature-spec.md`)

| # | Item | State |
|---|---|---|
| G1 | The visual standard: lab takeover, one lab frame with one header row, the title once, V3's lab anatomy in the Kit page | Done 2026-10-27 (D-60) and reviewed in the running app 2026-10-28 (D-64): masses beside the spring, graphs in the right column, the prediction asked first, dark-mode line art, phone top bar. Since then: illustrated scenes for refraction and pressure (D-65), and an apparatus bench of 26 reusable parts with motion on 25 Plans (D-66), so every library lab now draws its set-up. Open: the predict card is not an overlay; the chat repeats the key idea on a library answer |
| G2 | Bahasa Melayu (EN/BM switch, reviewed strings only) | Built 2026-10-27 (D-62) after the owner lifted the hold; every string is a draft until a fluent reviewer approves it (`eval/i18n/tools.py`). Since 2026-10-28 (D-68) drafts are shown by default with the "Draf" mark; set `BM_SHOW_DRAFTS=0` and `NEXT_PUBLIC_BM_DRAFTS=0` for reviewed-only |
| G3 | An exam item for the fermentation, Hooke's law hints | Done 2026-10-27 (D-61); five more exam items and hints on 24 more Plans |
| G4 | Orbit bench `kit-verified` with its citations proved; `kit-guardian` review of it | Citations proved 2026-10-27 (D-54). The review has not been run (agents start only on the owner's ask) |
| G5 | The demo's KOH titration question reaches the titration | Done: it routes to the titration (topic head 0.65), and a question that names a lab is answered by name when the head is unsure (D-59) |
| G6 | The four demo flows confirmed end to end in a real browser | Partly: the smoke covers Hooke through the real path, the takeover layout, Present and My progress (59 checks); the titration, fermentation and orbit flows are covered by the 30-Environment build and the verifier, not by clicking through the app |
| G7 | Numbers for the video (cost per lab, verified count, model count, L6 rate) | Counts are in STATUS (30 Environments, 35 science entries in the Kit manifest, the L6 rate in the evidence report); the cost per lab waits for W8 D1 (the owner's go) |

## Added 2026-10-27: Bahasa Melayu and the trained model (W12, W13)

| # | Item | State |
|---|---|---|
| H1 | A fluent reviewer reads the 30 Malay Plans, the 173 page strings and the Kit's fixed words | Skipped by the owner (2026-10-28); drafts are shown with their mark (D-68). Still possible: `uv run python -m eval.i18n.tools sheet review.csv`, then `import` |
| H2 | Malay questions: the router reads them through a glossary guard | Done (D-63): 19 to 57 percent answered from the library, all right, on a 68-question probe by the same author |
| H3 | The GPU job: NLLB translation and a multilingual encoder, against the guard | Written and tested on its pure parts, **not run**: needs a free GPU and the owner's sign-in (Kaggle `/mcp`, or a Colab notebook); `eval/models/colab/README.md` |
| H4 | Retrain the shippable router on the translated Malay | Waits for H3's files |
| H5 | Answer in Malay when asked in Malay | Not built: the explain prompt is English, so it is a prompt change with an eval delta (rule 7) and a paid run |
| H6 | Paste `BM_SHOW_DRAFTS` and `NEXT_PUBLIC_BM_DRAFTS` into `.env.example` | Owner (the file is blocked to my tools); both now default on, so the lines only document the off switch |

## Added 2026-10-28: the generation upgrade (W16)

| # | Item | State |
|---|---|---|
| I1 | Reusable apparatus parts (glassware, heat, weights, circuits, planets, particles, biology) that any Plan can combine | Done (D-66): 26 parts, motion under reduced-motion rules, planner v6 asks for a bench, 25 library benches, seven L6 bench rows all caught |
| I2 | Generate a lab for any related prompt | Done (D-67): the Free lane is on by default and draws a lab, labelled model-written; it runs only in live mode |
| I3 | More parts and bench arrangements by measured gap | Open: each new part needs its channels, words in both languages and a test; the paid run's Free and fallback counts show where |
| I4 | Bench animation that follows the physics (a pendulum's real period, an orbit's real speed) | Not planned: it would be a second simulation to verify; the parts show more or less in five buckets |

## Where each pending item is scheduled

The order is by dependency (see the plan for the reasons). W0 is done.

| Workstream | Items from this file |
|---|---|
| W0 Ground truth and decisions | F7, A9 (decided) |
| W1 L4 wording check and the Free lane | A9; the L4 gap in the verifier. **Built on fakes 2026-10-23 (D-41); its measurement is W8** |
| W2 Instant, free library hits | F1. **Done 2026-10-23 (D-42)**; flag-evicts-and-writes-a-regression-eval is still open |
| W3 V3 UI port | F2. **Done 2026-10-23 (D-38, D-43)**; a real-phone and screen-reader pass is W9 |
| W4 Interaction Kit and benches | F3; B8 (new models for the benches) |
| W5 Pedagogy | C1, C2 (with F4), C3 |
| W6 Reach | C4 (with F5), C5, F6, B4 |
| W7 Content and evidence | B1, B2, B3, B5, B8 |
| W8 Paid measurements | D1, D2, B6, and the L4 and Free canaries |
| W9 Trust, accessibility, CI | A3, A7, B9 |
| W10 Deploy gate | A4, A5, C6 |
| W11 People and the study | A6, A8 (decision), A10, E1 |

A8 (may a model-written Plan earn `kit-verified` through retrieved citations) is the owner's call and stays open until W11 or earlier; it does not block any workstream above.
