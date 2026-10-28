# Execution: W16, the generation upgrade

> Plan: `refdocs/plans/2026-10-28-w16-generation-upgrade.md`. Tests are written with the code and run once, at the end (the owner's cadence).

## Order of work

1. Kit: `apparatus.ts` (framework: bench layout, channels, words, guard, widgets), the parts, their CSS motion, the words in both languages, the manifest entry and the catalogue in the built manifest.
2. API: `Plan.apparatus`, PLAN-022, the assembler, the verifier's grounding of a part, the overlay's places, the manifest loader.
3. Data: benches on the library Plans; the Malay labels.
4. Prompts: planner v6, the Free pack v2, the Free lane on by default in live mode; the cost projection.
5. Malay on by default.
6. L6 rows; fixtures.
7. One combined verification; the paid measurement (up to $1.50); docs.

## Deviations and facts worth keeping

- 26 parts, not the planned "about 20": the bench Plans needed a gauge, a field, nuclei and coils that the first list did not have.
- Channel types are three (fraction, angle, pH), not one fraction type: a ramp angle and an indicator colour cannot be honestly drawn as a share of a "full".
- `full` is bounded both ways (at least the source's largest value, at most four times it). Without the upper bound a part could be drawn nearly empty at every slider position and still pass.
- The source range is evaluated at the corners of the slider box (`plan_checks._source_range`, `provenance._corner_range`). This is exact for the monotone models in the Kit and is recorded as a limit for any future non-monotone model.
- A part's widget count is per channel (`<kind>-<i>.<channel>`), so the part count comes from the widgets (`partsSoFar()`), not from a separate counter.
- The orbit part keeps an invisible twin circle so the audit sees its geometry while the visible body animates; the wave's wavelength is an owned CSS custom property (`--syn-wl`).
- Two drawing bugs found in the screenshots and fixed: a double translate on the syringe plunger and the trolley body (stray groups), and a gauge with no visible reading (a bar was added under the dial).
- A lone part draws larger (`.syn-app-bench:has(>.syn-app:only-child)`), so a one-part bench does not leave the stage half empty.
- 25 of the 30 library Plans got a bench, not 30: the other five (fermentation, titration, the cannonball orbit, refraction, Hooke's amali) already draw a bespoke scene of the same apparatus, and a second picture of it would only repeat it.
- heat_of_neutralisation carries the thermometer only: its model has no heat-supplied output to drive a burner honestly.
- The planner request is about 7.6k tokens by the chars/4 estimate, so the cap rose from 7000 to 8000 and the Kit pack from 15 to 17 entries (D-67). The provider counted about 10.6k input tokens for it in the paid run: the cap guards the estimate, and the cost projection already prices the high case at 3 characters per token.
- The paid measurement ran the 14-question breadth set: the full 24-question vertical set's hard bound ($2.08) did not fit the $1.74 left in the cap.
- The paid measurement found a prompt defect: the catalogue marked the pH and angle channels but not the fraction ones. Planner v7 (`prompt:`) says which channels need a `full`, that a fraction source must stay at zero or above, that a pH channel needs a pH output, and (after a second look) that °C is never "C" and the goal stays under 240 characters. Results in `refdocs/evidence/2026-10-28-w16-paid-measurement.md`.
- The combined verification found four things, all fixed: the apparatus's spoken sentence was not registered as Kit-owned (a label with a number, "chlorine-35", was refused at render); PLAN-022 was missing from the fail-check registry; the manifest `useWhen` was over 200 characters; the cost projection was stale after v7.
- The trace now records the parts a Plan chose (`plan_checks` ok, `parts`), so the next paid run can say which parts the planner uses.

## Status

Done 2026-10-28; verified in one combined run (CHANGELOG, STATUS ledger). Not done: a `kit-guardian` review of the parts, a paid measurement of the Free lane.
