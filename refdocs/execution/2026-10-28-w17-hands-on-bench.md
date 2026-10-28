# Execution: W17, a hands-on bench

> Plan: `refdocs/plans/2026-10-28-w17-hands-on-bench.md`. Tests are written with the code and run once, at the end (the owner's cadence).

## Order of work

1. Kit catalogue: a `grab` geometry per draggable channel (a line from the value-0 point to the value-full point, or a pivot for an angle), in the built manifest.
2. Kit apparatus: grips for channels bound to a control (snapped to the slider's step, `data-synapse-handle`, widget kind `handle`), the bench hint words, CSS; drops (`drop: {value, item}`: tray, tokens, the drawing as the drop zone, widget kind `masses`).
3. API: `ApparatusPart.drop`, PLAN-022 rules for a drop, the assembler (`snap` for a drop's slider, the `drop` option), the overlay place for the item word, `provenance` grounding of a handle, `render._drive_handles` and the Free-lane handle driver, refusal `handle_dead`.
4. Prompts: the catalogue line marks draggable channels; planner v8; free v3; cost projection.
5. Library: drops on two or three Plans; Malay words.
6. Tests and L6 rows; fixtures.
7. One combined verification; docs.

## Deviations and facts worth keeping

- 18 parts have a grab geometry, 16 grips appear on 13 of the 25 library benches. The other 12 benches draw only models' outputs (a current, a pressure, a decay), which have no slider to drag; the gauge, bulb, circuit, particles, nuclei, field, leaf and indicator have no grip because nothing on them is something a student sets by hand.
- Two drops, not "two or three": food energy (pieces of food onto the burner) and specific heat (cups of water into the beaker). The other Plans' sliders either have more than eight steps or are not added in portions.
- The tray was first inside the part's card. In a real browser at 480 px a narrow card wrapped eight items into four rows and the verifier's drag driver scrolled the tray off screen (`drag_dead`). The tray is now a full-width row under the bench, and the driver scrolls the smallest element holding both the drop place and the tray into view (`render._show_together`, also used for the mass hanger).
- A finger drag on a grip stopped short (0.8 of the way), most likely because the browser took the touch for a scroll and cancelled the pointer (the `touch-action` rule on the SVG shape did not stop it). A touch that starts on the grip now calls `preventDefault` on `touchstart` and `touchmove`; the rest of the drawing still scrolls.
- The first L6 row for a dead grip swallowed `pointermove` and would have been a surprise miss: the grip also takes its value on release. The row swallows `pointerdown`.
- The fixture `reference-heatbench` was regenerated (its Plan gained a drop); the other fixtures pick up grips from the new Kit with no change to their HTML, so their neutral rows exercise the grip driver too.
- `benches.py` (W16's scratch script) would drop the two drops if run again; the Plans are now the source of truth.
- Planner v8 and Free v3 are prompt changes with no paid measurement yet: the owner's earlier approval was for the measurement after W16 ($1.11 of $1.50 used); a measurement of v8 waits for the owner's go.
