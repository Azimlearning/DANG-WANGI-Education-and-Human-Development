# Misconception matcher: first measurement (2026-10-18)

> Hand-written. Reproduce with `uv run python eval/models/misconception_eval.py`. No model call. The probe set is `eval/models/misconception_probe.json`: 50 original questions, 20 in which a student states one of the 5 listed misconceptions, 20 neutral questions on the same topics, 10 off-topic. **The probe set and the matcher were both written by the build assistant, so they are not independent and the set is small.** Read this as "what the matcher does on a plausible reading", not as an accuracy to quote.

## Result at the shipped threshold (`min_score` 1.0)

| Question | Answer |
|---|---|
| Does the right misconception come first when a student states it? | **Yes, 20 of 20.** Wrong id: 0. Missed: 0 |
| Does it stay quiet on a neutral or off-topic question? | **No. It fires on 17 of 30 (57 percent).** |

Threshold sweep (recall on the 20 statements, false positives on the 30 quiet questions):

| `min_score` | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|---|
| recall | 100% | 100% | 100% | 100% | 100% | 100% | 85% |
| false positives | 57% | 37% | 33% | 17% | 10% | 10% | 3% |

## What it is

A topic detector, not a misconception detector. It scores word overlap with the entry's statement, topic and trigger phrases, so "What is osmosis?" matches the osmosis misconception exactly as strongly as a student who says water moves toward more water. The false positives are of three kinds:

- **Topical hits** on questions that merely mention the topic ("What is photosynthesis?", "State Newton's first law", "What is the difference between ionic and covalent bonds?" at 7.29, the highest score in the set). BM25 cannot tell these from a statement of the belief.
- **Weak noise** from shared common words: "State Ohm's law" scored 1.37 on the Newton entry, "Draw the electron arrangement of a water molecule" scored 2.70 on osmosis (the word `water`).
- Both vanish above about 3.0 on this set, at the price of the topical hits that remain (3 of 30).

## What this means for use

1. The pipeline feeds the best match to the explainer as context (`api/pipeline/run.py`, the lookup stage). At 1.0, over half of the questions with no belief to correct would carry a "common misconception" line. Whether that hurts the explanation is a prompt question the first paid run can answer; the match must not be shown to a student as a diagnosis.
2. **A match is the right trigger for a probe, not for a correction.** The P6 design (misconception follow-up) should use a topical match only to offer a probe question that lets the student reveal the belief, and correct only after the answer shows it. That is how the 57 percent becomes harmless.
3. The threshold was NOT changed. Raising it to about 3.0 looks right on this set (100 percent recall, 10 percent false positives), but the set was written by the same hand as the matcher and has 20 positives; choosing a threshold on it would be tuning on the test. Recheck on real student questions, then decide.
4. The list has 5 entries and every `source_verified` is false. The citations are bibliographic references recorded in Synapse v1 and have not been checked (Step 2).
