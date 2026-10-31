# Plan: W19, the generation pipeline v2: hands on every lab, a Free-leaning pipeline, a build log

> Written 2026-10-29 from the owner's review of the live gravity lab ("it doesn't have any drag and drop ... uses sliders ... no planets visual ... fix this and all other labs and questions"), and the follow-ups: "the compose and the free lane should be priority ... leaning more towards free", "a drop down option for user to see code being generated", "the 4 demo is perfect". Execution: `refdocs/execution/2026-10-29-w19-generation-pipeline-v2.md`. Decisions: D-76 to D-78. The owner's guide to the pipeline: `refdocs/guides/generation_pipeline.md`.

## What to build

1. **The planets bench** (D-78): `planetPicker`, `planetGravity`, `weight`; a library Plan `physics-f4-planet_gravity` with a spring balance (gravity feeds weight feeds Hooke's law) and a bar chart, cited to Form 4 Physics (the textbook's activity comparing the planets).
2. **Hands on every lab** (D-78): a handle on every graph point and on the cannonball's launch arrow; quiet controls keep their name and value; the verifier's handle driver takes a drawing box and a starting value.
3. **Chained models** (D-78) in Plans, followed by every plan check.
4. **Lanes** (D-76): `Plan.fit`, `LANE_PREFERENCE`, Free leads for a partial fit or a lab with no picture, with the Kit lab as the fallback; planner v9, free v4.
5. **Build log and code view** (D-77): `PlanDraft.components`, stage notes in the pipeline's words, the web dropdowns.
6. **The four demos** (Hooke, titration, fermentation, cannonball) checked in the browser.

## Done means

- Kit, web and API tests pass; L6 refuses its planted defects with no false positive; the hostile set 20 of 20; the library reseeded in English, all `kit-verified`; the four demos and the planets bench looked at in a browser.
- A paid check of the Free lane only within the owner's approved amount ($0.50 for this session, $0.08 spent before this workstream).

## Not in this workstream

A paid measurement of planner v9 across the breadth set; Malay overlays for the planets Plan (the owner asked for English only); new L6 rows for every new handle beyond the ones listed in the execution doc.
