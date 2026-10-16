# Audit: every enhancement we wanted for v4, against the v4 PRD

> Source of the wish list: `Synapse-V3/docs/ENHANCED_VERSION_PLAN.md` in the GenUI-Education repo (written 28 September 2026, commit 835a2ce), plus the owner's messages in this build. Each item is checked against `refdocs/synapse-v4-PRD.md` as it stood after P0. "Covered" means the PRD names it in a phase with an exit criterion. "Gap" means it was missing or too vague to build from, and the last column says what changed.

This is a planning document, not a measurement. It was written by reading both documents side by side.

## 1. The enhancement plan's own items

| ID | Enhancement | v4 PRD status | Where it lives now | Resolution |
|---|---|---|---|---|
| N1 | Declared physics contract: formal governing model, metamorphic relations, checked before HTML | Covered, reshaped | Science micro-models with an independent reference and properties (hard constraint 6); L3 cross-check | P1 registration suite includes metamorphic relations (doubling a load doubles the extension, monotonic in each input) |
| N2 | Verifier mutation testing: inject physics bugs, measure detection | Covered | L6 | P1 builds the baseline over planted variants of generated Environments and reports the detection rate per layer |
| N3 | Solvability and fuzz checks: extremes, NaN, frozen canvas, success state reachable | Covered, "success state reachable" was missing | L2 (grid and extremes) | P1 does grid, extremes, finite readouts and no errors. The reachable goal state belongs to a task, so it moves to P6 with challenge levels |
| N4 | Promotion ladder: generated, verified, cached, audited, canonical, with eviction and staleness | Covered | PRD 3.8 trust ladder; P5 | None |
| N5 | Amali mode: problem, hypothesis, variables, procedure, results scaffold, tied to the SPM practicals | Named in P6, **no catalogue of experiments to build it from** | New: the experiment catalogue | D-19. Schema and tooling in P2, authoring in P4, Amali scaffold components in P6 |
| N6 | Textbook citation on every library Environment | Covered | P2 evidence, citation chips | None |
| N7 | Misconception-first entry, predict-observe-explain with `when` predicates | Covered in P6; the seed list is 5 entries | P6; matcher in the models track | Port the v1 list with provenance in P6; expand only with citations checked locally; matcher is retrieval, not trained (D-20) |
| N8 | Device-local learner map over the syllabus, with an export code | Mastery covered, **the map and the export code were not** | P6 | P6 now names the learner map and the export code |
| N9 | Overnight gap filling with the Batch API | Covered | P5 | Batch pricing must be re-checked and the owner confirms the run (rule 7) |
| N10 | Visible checks: show what was checked, not a generic badge | Principle 5 and constraint 11, **no specific panel** | Provenance component | The stored `checked` record is extended in P1 (controls, grid points, reference cases) and shown as a "What was checked" panel in P1/P3 |
| N11 | Audit queue page; a flag writes a regression eval | Review queue named, **auto regression eval was not** | P5 | P5 adds flag-to-regression-eval |
| N12 | KSSM concept graph for revision | Not scheduled (graph retrieval is a non-goal, D-12; a prerequisite map is different) | none | **Parked**, as in the source plan. Not dropped: revisit after P6 |

## 2. Round-one ideas re-read in the source plan

| ID | Idea | v4 PRD status | Resolution |
|---|---|---|---|
| IDEA-0001 / X1 | Syllabus library, subject, form, chapter, topic | Covered (P5 Shelf) | None |
| IDEA-0015 | Run the deferred golden and hostile evals | Constraint 9; **the v3 hostile set was not yet ported** | Port `evals/hostile.yaml` with provenance (P1); golden set defined per vertical and mapped to KSSM topics (P3), fixing the source plan's F6 |
| IDEA-0003 | Distilled router in production | "Route" stage names a local classifier, **no module, data or training plan** | New models track (D-20) |
| X3 | Curriculum-grounded verifier | Evidence plus L4, notation and scope check not named | P3: L4 receives the retrieved passage and checks notation and scope |
| X2 / IDEA-0007 | SPM mode, exam-mirror, marking scheme graded against live state | Covered (P6 exam mirror) | None |
| IDEA-0013 | In-artifact concept check | Covered (merged into predict tasks) | None |
| X4 / IDEA-0008 | Forwardable link, offline | Covered (P7) | M1 chapter pack for school PCs added to P7 |
| IDEA-0009 | Bahasa Melayu for audited labs only | Covered (P7) | None |
| IDEA-0005 | Tutor loop from bridge events | Companion and the bridge's model-visible summary exist; **the loop itself was implicit** | P6 names it |
| IDEA-0006 | Remix: "add air resistance" | Edit-not-regenerate accelerator (P5) | P5 names remix as its acceptance test |
| IDEA-0002 | Phone-first redesign | Principle 6, constraint 10; P4 phone checks | None |
| IDEA-0011 | Accounts | Dormant by decision (D-11); N8 covers progress | None |

## 3. Plan-level items

| Item | v4 PRD status | Resolution |
|---|---|---|
| Headline metrics (coverage %, p50 time-to-lab, cost per student per week, mutant detection rate, hostile block rate, golden pass rate, learning gain) | **Not in the PRD** | Added to the PRD as the evaluation deliverables, with which phase produces each |
| D1 restate "no predefined library" rule | Covered by D-03 | None |
| D3 storage: SQLite local, managed database at deploy | Covered (3.10) | None |
| D4 cost ceiling: library free, new generation limited, monthly cap | Monthly cap covered (D-08); rate limits deferred (D-11) | P7 adds a cost dashboard built from the ledger and traces |
| D5 curriculum alignment and Bahasa Melayu in; accounts, payments, teacher dashboard out | Covered | None |
| D6 name before public launch | A-14 | Unchanged, open |
| Phase F learner study with consent through UTP | Covered (P8) | Needs the owner; cannot be done in the cloud |
| Amali timing: SPM practical tests reported for November 2026 | Not in the PRD | Dropped by the owner (2026-10-16): the exam calendar has nothing to do with the project, so no dates are tracked |

## 4. From the external landscape (source plan section 2)

| Finding | Implication already in v4 | New |
|---|---|---|
| Google learning interactives: vetted library, hints, levels, worked solutions, solvability checks | Library, trust ladder, hint ladder, worked solution, grid and extremes | **Challenge levels** are not in the Kit's pedagogy list; added as an optional pedagogy component (P6) |
| PDE-grounded verification: 39 to 40 percent of generated simulations run but solve the wrong physics | L3 cross-check against an independent reference | None |
| Neshaei et al.: generate at runtime for coverage, promote to an audited library for scale | The whole lane and ladder design | None |
| Kurikulum Persekolahan 2027 does not touch Form 4 or 5 until about 2030 (an inference in the source) | The 53-topic taxonomy keeps its shelf life | None |

## 5. New in this session (the owner's messages)

| Request | Resolution |
|---|---|
| Choose a first vertical yourself | D-18: Physics Form 5 (force and elasticity, forces and pressure, electricity), provisional |
| By the end there should be many experiments and Environments, at least 3 from each subject | D-19: an end-state target of at least 9 verified Environments (3 each in Physics, Chemistry, Biology), each tied to a catalogued KSSM experiment or topic |
| "We have docs of all the available experiments" | The textbooks are not in any repo and the four Chemistry experiment books are image-only. D-19 adds an experiment catalogue: the schema and tooling are built in the cloud, the text-derived fields are filled locally. Titles seeded in the cloud are marked unverified |
| A trained-model component, a few kinds if needed | D-20: a models track. Kinds: a multi-head router (topic, domain, pattern, complexity) trained on the committed v3 dataset, and a misconception matcher built as retrieval. Each is measured against a baseline before it may gate anything |
| Do as much as possible in the cloud, move to local at the end | D-22: cloud-first, with a "Deferred to local" register in STATUS as the hand-off |
| Mark 3: research how ChatGPT's UI works; deep prompt templates, fail checks, micro-components, layers, skeletons | D-23 and `2026-10-16-p3-mark3-pipeline.md`: eleven layers, plan as data, generation skeletons plus a loading skeleton, versioned prompt packs, a fail-check registry tied to the code, generation micro-components, `useWhen` retrieval. Research note written; it rests on search summaries |

## 6. What is still not decided

- Whether a dense embedding model beats TF-IDF for retrieval and routing (A-9, D-12). Measuring it needs a model download this container may not be able to make, so it is listed as a local follow-up.
- The corpus legal position (A-8), the isolation choice for a public deploy (A-10, a spike is in P1), and the name (A-14).
