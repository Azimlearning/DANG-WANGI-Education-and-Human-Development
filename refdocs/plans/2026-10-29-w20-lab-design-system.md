# Plan: W20, the four demos' design as the rule for every generated lab

> Written 2026-10-29 from the owner's request: "considering all u did to ensure the 4 labs works, take this system design and use it to enhance our genui pipeline so when i ask it to generate an experiment or simulation when asking any question". Standing rule (memory): drag-and-drop and animation over sliders and buttons. Decision: D-80. Execution: `refdocs/execution/2026-10-29-w20-lab-design-system.md`.

## The design, as the four demos have it

1. A drawing of the real apparatus or system (stand and spring, burette and flask, tubes and limewater, Earth and cannon).
2. Every quantity the student changes is operated on the drawing (masses dropped on a hanger, the stopcock held, the dial turned, the arrow dragged); the slider is only the keyboard path, drawn quiet.
3. Motion that explains (a mass drops in, drops fall, bubbles rise, the ball flies).
4. The same page shape: kicker, title, try this, key idea, predict, steps, the bench beside the readouts, results, a short explanation.

## What to build

1. **Compose, guaranteed in code** (no paid call): after the plan checks pass, any control that the student cannot drag (no masses, planets, valve or dial surface, no `[drag]` bench channel bound to it, not the x of a graph) gets a graph of a readout that depends on it, whose point is a handle (D-78). Up to the Plan's two graphs; checked again after.
2. **Compose, by the planner**: planner v10 states the four-demo rubric.
3. **Free**: free v6 carries a house-style page skeleton (the Kit's look: colours, cards, fonts, layout, dark mode) and the interaction and motion patterns of the demos, including drag-onto-a-target.
4. **Verifier**: a Free handle may name a drop target (`data-synapse-target="<element id>"`); the verifier drags the handle onto it and the slider must change, as for any handle.

## Done means

Pipeline, verifier and prompt tests on fakes; the Free handle driver tested on a page with a target; no Kit change (the library stays valid). A paid measurement only when the owner runs prompts.

## Not in this workstream

A Kit part per new apparatus; a predict card or buttons in Free pages (the Free contract allows sliders only).
