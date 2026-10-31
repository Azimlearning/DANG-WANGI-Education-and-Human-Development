# Execution: W20, the four demos' design as the rule for every generated lab

> Plan: `refdocs/plans/2026-10-29-w20-lab-design-system.md`. Decision: D-80. Tests written with the code; one combined run at the end (the owner's cadence).

## Order of work (as done)

1. Compose, in code: `plan_checks.hands_on()` gives any control with no drag surface a graph of a readout that depends on it, whose point is a handle (D-78); `run.py` applies it before the lane decision, and the plan checks run again on the result.
2. Library: five Plans gained a hands-on graph (magnification, newton_second, electrical_energy, ohm_explorer, parallel_resistance), each with its Malay overlay entries; the planets Plan got its Malay overlay (`data/i18n/ms/planet_gravity.json`) so the overlay check holds, though the demo is English only.
3. Verifier: `_drive_handles` puts every other control at its default before it drags a grip (the sweeps before it leave controls at their ends, and the Ohm graph had nothing to move at 0 V).
4. Verifier, Free: a handle with `data-synapse-target="<element id>"` is dropped onto that element and the slider must move (`_drive_free_handles`); tests for a working drop, a missing target and a dead drop.
5. Prompts: free v6 (the demos' page shape, the Kit's colours as a CSS skeleton, motion patterns, drag along or drop onto), planner v10 (a four-point self-check against the demos). Cost projection regenerated (`eval/cost/project.py`, no paid call).
6. A lab for every question: `run._last_resort` (the full Free page if never tried, then `_simple_page`, up to `SIMPLE_ATTEMPTS` = 3, each told the last refusal's reason) runs whenever the layers end in `text_only` after routing; `_Run.extra_calls` and `_allow` give it its own call allowance; `free_simple.v1.md`; `prompts.simple_request`; `GENERATION_TIER` (`Deps.generation_tier`, `prompts._writer`: heavy is Opus at medium effort, four times the output room, capped by our guard of 32,000 tokens); the provider waits 300 s (a heavy plan call does not stream); the web clears the "no lab" note when a lab arrives. A first version served the closest stored lab instead (`_related_lab`); the owner rejected it the same hour and it was removed. `library.content_words` and `lab_words` stay (the coverage rule uses them).
7. Reader: `wording.parse_verdict` drops an issue the reader itself cleared ("... no error there") and passes a verdict whose every reason was self-cleared; the cleared lines are kept in the trace.

## Deviations and facts worth keeping

- Not in the plan: the last step (step 6), the heavy tier, and the reader filter (step 7). All came from live testing: a spring question was refused because the reader listed a point it had just called correct, and the owner's rule is that every question ends with a lab made for it ("worst case we make simple"), on a stronger model for demo day.
- The first rebuild stopped at the Ohm lab: "dragging the handle graph.resistance changed no readout". The cause was the verifier's order, not the lab (step 3). All five changed Plans then verified `kit-verified` in Chromium.
- "revise", "learn", "understand", "explain" and "teach" joined the asking words: "How do I revise Hooke's law?" was being sent to the planner because "revise" is not in the Hooke lab.
- Three library run tests and one prompt test were stale since W19 (remembered questions are served before the router; the plan reader is on the standard tier). They now test what they meant to.
- The cost projection still assumes 2500 to 6000 output tokens for a Free page and the standard tier; it does not model the last step or the heavy tier. Not changed this session.
- Under the `kit` preference a twice-refused plan used to end in words; it now ends with the last step's page (the test was rewritten to the owner's new rule).
