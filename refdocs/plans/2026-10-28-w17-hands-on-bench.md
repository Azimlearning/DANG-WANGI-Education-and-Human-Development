# Plan: W17, a hands-on bench: drag the apparatus, drop things into it

> Written 2026-10-28, from the owner's request: "it is more better to have it be more interactive and drag and drop like the 3 demo on synapse v3 and the synapse v4 demo but this time is for any prompt and also yeah more interactable and drag and drop". Execution: `refdocs/execution/2026-10-28-w17-hands-on-bench.md`. Decisions: D-69 to D-71.

## What V3 and the demo video do that V4's generated labs do not

V3's labs (`Synapse-V3/backend/services/builtin_labs.py`, `hookes_law_lab.py`, `yeast_fermentation_lab.py`) are operated on the drawing: drag the pipette onto the flask, the stopcock down, the eye to the meniscus, a mass onto the hanger, yeast and oil into the tubes, the timer dial round. V4 has the same gestures only inside four fixed parts (mass hanger, dial, valve, the titration eye). The 26 bench parts of W16 (D-66) only show numbers. A generated lab is still operated by sliders.

## What to build

1. **Grab handles on the bench** (D-69). Every apparatus channel bound to a slider gets a grip on the drawing where that quantity is: the top of a beaker's liquid, the syringe's plunger, the trolley, the block on a ramp, the pendulum's bob, the spring's hanger, a coil's last turn, the planet's orbit, the cell's edge, the burner's flame. The student drags it; the slider follows, snapped to its steps, and everything bound to it redraws. Automatic: no Plan change, so every bench in the library and every generated one becomes hands-on. The slider stays as the keyboard and screen-reader path (the grip is a pointer surface, like the dial's knob). The verifier drags every grip with a mouse and a finger and refuses a page whose grips do not move their control (`handle_dead`), or that has grips the Kit did not make.
2. **Drop things into a part** (D-70). A Plan may give a part a `drop`: a tray of items ("Spoon of salt", "Drop of acid", "Slotted mass", "Cell") the student drags onto the part's drawing, each one step of a slider with 2 to 8 steps. Taking one out goes back a step. Keyboard: Enter or Space on an item moves it. It reuses the mass hanger's contract, so the verifier's existing drag driver checks it (every item on, every item off, keyboard, finger).
3. **The Free lane may draw handles** (D-71). A model-written page may mark a drawn element `data-synapse-handle="<slider id>"` as a pointer surface for that slider. The verifier drags each one both ways and requires the slider to move; the slider is still the only control and the source of every number.
4. **The planner learns it**: the apparatus catalogue in the planner prompt marks the draggable channels; planner v8 says to bind the part a student would handle directly to the slider they vary, and when to use a drop. Free prompt v3 describes handles.
5. **Library**: the benches gain grips wherever a channel is bound to a slider; two or three Plans gain a drop where the experiment adds things in steps.

## Done means

- Every grip and drop works by mouse, finger and keyboard (through the slider or the item buttons), at 360 px, in both languages and themes, with reduced motion.
- A page that kills, adds or misplaces a grip or a drop item is refused (verifier tests and L6 rows).
- The whole library verifies; one combined run at the end. A paid measurement of planner v8 only on the owner's go.

## Not in this workstream

Multi-step set-up sequences (V3's "yeast, then oil, then delivery tubes" gate), swirling, free placement of apparatus anywhere on the bench. Each needs its own contract and verifier driver; recorded as next steps.
