# Plan: W16, the generation upgrade: an apparatus library, richer templates and a freer Free lane

> Written 2026-10-28, from the owner's request: "the ui generated / sandbox / simulation generated is not as visual or interactive as synapse3 and the v4 demo video ... increase the amount of templates, and prebuilt components (that are replicable across multiple experiments and scenarios) example like beaker movements, or weights or chemical or planets". Answers given before work began: the Malay drafts are shown by default with the draft mark; generation may go beyond verified parts ("u should be able to generate anything related to simulation or experiments"); one paid measurement after the upgrade, up to $1.50. Execution: `refdocs/execution/2026-10-28-w16-generation-upgrade.md`. Decisions: D-66 to D-68.

## Why the pages look plain today

A Compose page is assembled from a Plan by two skeletons. The Plan can name sliders, readouts, graphs, a table, words and at most one of six bespoke scenes. Each scene is hand-built for one experiment (a spring, a burette, two yeast tubes, a cannon, a ray, a tank). So most questions get sliders and a graph, and a new picture needs a new Kit part, a new schema kind and new checks. The Free lane, the only other way to get a picture, is told "sliders only, nothing moves".

## The design

1. **An apparatus library in the Kit** (`Synapse.apparatus`): about twenty reusable parts (glassware, heat, measurement, mechanics, electricity, waves, space, particles, biology), each with named **channels** (a beaker's `level`, a burner's `heat`, a bulb's `brightness`, an orbit's `speed`). A Plan places up to four parts on the bench and binds each channel to a control or a model instance, with a drawing scale. One generic rule set covers all of them: a channel draws a number it was given and never prints one; the audit keeps every attribute; the plan checks and the verifier check each channel's source, unit and scale. A new experiment needs no new code, only a new arrangement of parts.
2. **Motion**: parts animate (a flame flickers, bubbles rise, current flows, a planet goes round, a wave travels, particles jostle, a pendulum swings) with CSS animations in the Kit's own stylesheet. Motion never changes a number, it follows a channel by speed class, and it stops under reduced motion (the verifier already checks that).
3. **The planner learns the library**: a new planner pack version lists every part, its channels and when to use it, and asks for a bench whenever the experiment has apparatus. The 30 library Plans get benches.
4. **A freer Free lane**: a new Free pack lets the model draw with SVG or canvas and animate, on the same honesty rules (labelled model-written, never `canonical`, read by a second model, run in a real browser, motion off under reduced motion). The Free lane is on by default when the API runs live.
5. **Bahasa Melayu on by default**, the draft mark kept.

## Exit criteria

- Every part draws in both languages, light and dark, at 360 px, refuses an unbound or misbound channel, and is refused by the verifier when a page falsifies it (L6 rows).
- The library's labs verify with their benches, English and Malay.
- One paid measurement of the new planner on the golden questions, under $1.50, reported (pass rate, parts used, cost).
