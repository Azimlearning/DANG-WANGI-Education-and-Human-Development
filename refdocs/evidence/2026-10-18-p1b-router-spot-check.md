# Router spot check: 50 held-out questions judged against the science (2026-10-18)

> Hand-written, not generated. Reproduce the sample with `uv run python eval/models/spot_check.py` (seed 20261018, the first 50 of `data/models/router/test.jsonl` after a shuffle). No model call was made.
> **Who judged:** the build assistant (a language model), from its knowledge of the KSSM Form 4 and 5 science syllabus, NOT a teacher and not the textbook. Model-judged scores are never the primary metric (CLAUDE.md, hard constraint 9). Treat this as a screening pass that finds problems to look at, and have a teacher confirm the items marked `?`. n = 50 gives wide error bars (a 94 percent rate here is roughly 84 to 98 percent at 95 percent confidence).

The model card measures agreement with the teacher labels. That is a different number from being right, so this pass reads each question and asks only: is the router's label right?

## Result

| Head (gate threshold) | Router right | Notes |
|---|---|---|
| domain (0.367; all 50 pass it) | **47 of 50** (94 percent) | Wrong: q10, q27, q47 (below) |
| topic (0.182), the 42 predictions the gate lets through | **36 of 42** (86 percent), one more doubtful | Wrong: q01, q17, q21, q26, q32, q45; `?` q18 |
| pattern (0.648), the 16 predictions the gate lets through | 16 of 16 sensible | Judged for plausibility only; there is no single true pattern |
| complexity (0.833) | not judged | It is a matter of taste and the card already calls the head weak |

For comparison, the teacher's own domain label is right on 47 of 50 by the same reading (q10, q27 and q34 are wrong in the teacher's data), which is why agreement with the teacher and being right are not the same number.

## What was wrong

- **q27** "What is the relative mass of a proton compared to a neutron?": the router says domain `physics` (0.74) while its topic head says `chemistry_form4_matter_and_atomic_structure` (0.66), which is right. The teacher made the same domain error, so training could not correct it.
- **q10** "Why does vitamin C content vary between different fruit juices when tested?": domain `chemistry` (0.73) but topic `biology_form4_digestion` (0.82). The topic is the better call (a food test in the nutrition chapter); the teacher also said chemistry.
- **q47** compensation point: domain `earth_space` (0.49); it is biology (photosynthesis). The teacher said biology.
- Topic errors, all at low confidence: q01 vibrating string and wavelength went to `physics_form5_quantum_physics` (0.23, should be waves); q17 blood clotting went to `immunity` (0.32, should be the circulatory system); q21 carrier proteins went to `chemical_composition_of_cell` (0.50, should be movement of substances); q26 natural selection in bacteria went to `biodiversity` (0.23, inheritance and variation); q32 metal displacement went to `thermochemistry` (0.21, redox); q45 seedling growth went to `response_in_plants` (0.50, plant growth).
- q05 and q48 were also wrong on topic but at 0.13, below the gate, so the LLM fallback decides them. That is the gate working.

## What this says

1. **The topic gate is permissive.** All 6 wrong topic calls got through the gate: four sit between 0.21 and 0.32 and two at 0.50. At a threshold of 0.55 none of this sample's wrong calls would pass, at a price in coverage (more LLM fallback calls, so more cost). n = 50 cannot set a threshold; it is a reason to recheck the gate on the full relabelled data. Nothing was changed.
2. **Disagreement between heads is a free signal.** In q10 and q27 the domain head and the topic head disagree, and in both the topic head was right. A rule "if a confident topic implies a different domain, trust the topic" would have fixed both. Not implemented: two cases are not evidence.
3. **The teacher makes mistakes the router inherits.** Three of the 50 teacher domain labels are wrong, so a router that agrees with the teacher 92.6 percent of the time cannot be assumed to be right 92.6 percent of the time.
4. The pipeline has a second line of defence for topic errors: PLAN-016 refuses a science model used under a topic the Kit does not list, so a wrong topic costs a wasted plan, not a wrong Environment. It does not stop a student getting a correct Environment for the wrong question.

## What would make this a measurement

A person who teaches KSSM judges 200 or more, blind to the router and the teacher, and the per-head rate is reported with its interval. This file is only the screening pass.
