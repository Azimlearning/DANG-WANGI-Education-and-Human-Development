# Misconception probe: the threshold (2026-10-25)

> Hand-written. Reproduce: the sweep with `uv run python eval/models/misconception_eval.py`, and the probe-specific counts with the snippet under "How". No model call. The probe set is the 50 questions in `eval/models/misconception_probe.json`, written by the same author as the matcher, so this measures a plausible reading and not students.

## What was chosen

A probe is offered when the best-matching entry that has a probe scores at least **3.0** (`PROBE_MIN_SCORE` in `api/models/probes.py`). The old matcher threshold of 1.0 stays for the explain prompt.

## Result at 3.0

| Measure | Value |
|---|---|
| Positive statements of the five listed misconceptions that get their own probe | 20 of 20 (measured first on the three flagship ones, 12 of 12, then on all five) |
| Positive statements that get another entry's probe | 0 of 20 |
| Neutral or off-topic questions that get a probe | 3 of 30 |

The three that fire are "How is an ionic bond formed between sodium and chlorine?", "What is the difference between ionic and covalent bonds?" and "State Newton's first law of motion." Each is about the probe's own topic, so a quick check there is reasonable rather than a stray card.

## From the full sweep (any entry, for comparison)

Recall 100 percent from 0.5 to 4.0 and 85 percent at 5.0; false positives 57 percent at 1.0, 37 percent at 1.5, 17 percent at 2.5, 10 percent at 3.0 and 4.0, 3 percent at 5.0. 3.0 is the lowest threshold with the lowest false-positive rate that keeps recall.

## What this does not show

It does not show how real students phrase a misconception, and it does not show that the probe teaches anything. The correction wording has not been read against a textbook page or by a teacher; the card says so.
