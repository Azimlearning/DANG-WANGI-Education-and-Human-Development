# Plan: W4, the interaction Kit and the V3 benches rebuilt as Kit components

> Roadmap: `refdocs/plans/2026-10-22-completion-roadmap.md` (W4). Written after the first stage was built; kept true to what happened (CLAUDE.md rules 2 and 4). No paid call is made by anything here.

## Why

Synapse V3's four benches (Hooke's law with draggable masses, titration with a stopcock and an eye-level reading, yeast fermentation with tubes and a dial, an orbit scene) are raw HTML strings with their own palettes and unchecked physics. The demo video shows them. To be shown in V4 they must be built from **Kit micro-components with cited, independently referenced models**, and the verifier must **drive the gestures** (D-17: verification presses real input), or they cannot carry any label above `model-checked`.

## Stages (one at a time; the next starts when the previous is green end to end)

| Stage | Bench | New Kit parts | New model | Status |
|---|---|---|---|---|
| 1 | Hooke's law: hang masses on a spring | `massHanger` (control), `springScene` (scene), the audit's `widgets` report, the slider `snap` option | none (`mechanics.hookes` exists) | **Done 2026-10-24** (this plan, section "Stage 1") |
| 2 | Titration: stopcock, burette, eye level | `valve`, `buretteScene`, `eyeLevel` | none (`chemistry.titration` exists) | Not started |
| 3 | Yeast fermentation: tubes and a dial | `dial`, tube scene | a cited respiration-rate model (Biology) | Not started |
| 4 | Orbit | `orbitScene` | a cited gravitation/orbit model (Physics F4) | Not started |

Each stage gets: a written precondition and accessibility fence per component, a registration suite that refuses every planted defect, a harness drive of the gesture, citations from the local corpus for any new model, an independent hand-written reference, L6 rows, and a `kit-guardian` review before the relock is committed.

## Stage 1 design

- **`massHanger(env, {id,label,unit,min,max,value,grid})`** is a control with a different surface. It is built on `slider`, so the labelled range input is still on the page, still `data-synapse-control`, and every sweep, provenance and reference check is a slider's. `grid` is the number of masses (2 to 8). The masses are Kit action buttons (a letter, never a number) that can be dragged (pointer events, pointer captured: mouse, pen, touch) or pressed (Enter, Space, a tap). The control snaps every value to a whole number of masses, so a script cannot set half a mass.
- **`springScene(env, {extension, full})`** draws a spring whose length follows the extension. It accepts only the output of `mechanics.hookes`, writes words only (no number), and is held to its drawing by the audit.
- **The audit's `widgets` report** is how a composite widget answers for itself, in two halves. **Structure** (cheap, no false alarms, also acted on by the student's runtime self-check): each mass is in the part the control says, not hidden or restyled by attribute, the Tray and Hanger captions are Kit-owned text, the scene's polyline, pan, label and stroke are what the Kit drew, and it is still on the stage. **Layout** (read from a real layout, in view; acted on only by the verifier): the bench and its parts have a usable size, each mass sits inside its part, is not faded and is not covered by another element, and the spring's pan sits where the extension puts it at the picture's real scale. Any problem is a refusal (`widget_tampered`, L1-022). The verifier also holds the scene to the plan: its chain counts as a model use (`plan_mismatch` for a second instance), its input units are checked, and its `full` scale must fit the model (`scene_scale`, L1-024). A scene not drawing `mechanics.hookes` is `scene_ungrounded` (L1-023).
- **The harness (`api/verify/render.py` `_drive_drags`)** takes what must exist from the audit, never from page markers. It drags every mass onto the hanger with the mouse (each must raise the control by exactly one step and move the readouts), drags every mass off, presses every mass from the keyboard (Enter to hang, Space to take off), and drags every mass onto and off the hanger with a finger (CDP touch). A dead or blocked mass is `drag_dead` (L2-006). A Playwright failure is a harness error (fail closed), not evidence about the masses.
- **Plan fields and checks.** `ControlSpec.surface` (`slider` default, or `masses`) and `Plan.scene` (`kind: spring`, `source`, `full`). PLAN-018: a masses control needs 2 to 8 masses and a start on a whole number of masses. PLAN-019: a scene must draw a model instance of an allowed model, and its `full` scale must lie between the model's output at the controls' maximum and twice that.
- **Not a new trust claim.** A mass bench is `kit-verified` only under the existing rule (a textbook citation); the bench adds no citation of its own.

## Prompt change

The Plan schema grew two fields, the Hooke exemplar now carries masses and a scene, and the planner now receives the schema as compact JSON (the file stays indented for review). The pack is versioned `planner.v3` (same words as v2) so a later measurement names the request it measured. The planner request had reached the 7000-token cap; compacting removes about 40 percent of the schema's tokens with no change in content. This is a `prompt:` change (CLAUDE.md rule 7). **Eval delta: none measured.** No paid planner run was made (fakes are the default and a paid run needs the owner's go); the offline request-size projection was regenerated (`refdocs/evidence/2026-10-16-p3-cost-projection.md`). The first live planner canary after this (W8) is the delta, and it must be compared with the 2026-10-18 no-exemplar result (3 of 3 at first attempt).

## Out of scope for stage 1

The titration, yeast and orbit benches; Bahasa Melayu strings for the new components (W6); the Amali record path (W5); any change to how the web hosts a frame.

## Known limits (recorded, not hidden)

- **A pointer-transparent sheet laid over the bench** hides the masses without disturbing hit testing; the audit reads layout, not pixels. A recorded L6 known miss (`drag-overlay-pointer-transparent`); only a pixel check would catch it.
- The student's self-check acts on structure only, so a style rule that moves a mass in a student's browser is caught only if the verifier saw it first (pages are assembled from the Plan, so the verified page is the page).
- The verifier checks the light theme only.
- The runtime self-check re-audits on every pointer move (pre-existing cost, now with two more checks).
- On a phone the controls sit below the stage, so the masses and the spring are far apart; a layout choice, not a defect of the checks.
