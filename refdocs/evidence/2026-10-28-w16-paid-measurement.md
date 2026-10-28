# W16 paid measurement: the planner with the apparatus bench (2026-10-28)

> The owner approved "after the upgrade, up to $1.50". Three runs, $1.1122 in total, all through the LLM seam and the spend ledger. No exemplar was shown to the planner (`--no-exemplar`), so these measure planning, not copying. Raw results: `eval/golden/results/20261027T224821Z-live.json`, `20261027T225609Z-live.json`, `20261027T225911Z-live.json`.

## Why the breadth set

The full 24-question vertical set projected a hard bound of $2.08, more than the $1.74 left under the cap, so it could not be sent. The 14-question breadth set (Biology and Chemistry, Form 4 and Form 5) projected $0.32 to $0.68, hard bound $1.22.

## Run 1: planner v6, all 14 breadth questions ($0.7387)

| Result | Count |
|---|---|
| An Environment delivered (Compose lane, `model-checked`) | 13 of 14 |
| First plan accepted | 5 of 14 |
| First plan refused by PLAN-022 (the bench) | 5 of 14 (b05, b06, b09, b11, b12) |
| No Environment | 1 (b09: PLAN-010 then PLAN-022, an indicator's pH bound to a concentration) |

What PLAN-022 refused, every time correctly:
- a thermometer's temperature or a leaf's light with no `full` (3): the catalogue marked the pH and angle channels but not the fraction ones, so the model could not tell which channels need a `full`;
- a leaf's rate bound to a net photosynthesis rate that goes below zero (2);
- an indicator's pH bound to a concentration in mol/dm3 (1).

Average cost per question $0.053; per delivered Environment $0.057. The label is `model-checked` throughout because the run's temporary store has no corpus and the generated Plans name no citation; that is the expected label, not a regression.

## The fix: planner v7 (`prompt:` change)

v7 says that every unmarked channel is a fraction channel and names the thermometer, leaf and gauge; that a fraction channel's source must stay at zero or above; that a pH channel needs a model output in pH. After run 2 it also says to copy units exactly ("°C", never "C", the coulomb) and to keep the goal under 240 characters.

## Run 2: v7 (first draft) on the five PLAN-022 questions and one control ($0.2710)

| Question | v6 first attempt | v7 first attempt | v7 result |
|---|---|---|---|
| b01 (control) | ok | ok | Environment |
| b05 | PLAN-022 | ok | Environment |
| b06 | PLAN-022 | ok | Environment |
| b09 | PLAN-010 | ok | Environment (none under v6) |
| b11 | PLAN-016, 004, 022 | PLAN-016, 004 | Environment |
| b12 | PLAN-004, 022 | PLAN-004 | none: retry broke the 240-character goal limit (PLAN-001) |

PLAN-022 on the first attempt: 5 of 5 under v6, 0 of 5 under v7.

## Run 3: v7 as amended, on b11 and b12 ($0.1025)

b12 planned at the first attempt and delivered; b11 was refused once for PLAN-016 (the router placed a Form 5 thermochemistry question in the Form 4 acids topic; the model is registered for Form 5) and delivered on the retry. PLAN-004 did not recur.

## What this shows and does not show

- The bench checks catch real planner mistakes and the retry recovers most of them; the clearer catalogue removed the bench refusals from the questions measured.
- Small samples by one author: 6 and 2 questions after the fix, not a re-run of all 14. The delta is a direction, not a rate.
- These results do not record which parts each delivered page drew (the pages lived in a temporary store). Since this run the trace records them (`plan_checks` ok carries `parts`), so the next paid run will say.
- PLAN-016 is a router issue (Form 4 versus Form 5 thermochemistry), not a planner one.
