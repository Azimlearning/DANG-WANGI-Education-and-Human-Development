# Plan: W15, illustrated scenes for the labs that have only a graph

> Written 2026-10-28 (after the first two scenes were built; see the execution doc). Execution: `refdocs/execution/2026-10-28-w15-illustrated-scenes.md`. Decision: D-65.

## What and why

Of the 30 labs, 26 had a graph and readouts but no picture of the thing being measured; the demo video and V3 show apparatus. A scene in V4 is not decoration: it is a Kit part that draws a model's number and is held to it by the audit and the verifier, so a picture can never disagree with the readout.

## Scope

**In, this block:** a refraction scene (a ray from air into a denser medium at the computed angles) and a pressure tank (a probe as deep as the pressure says, with arrows that grow with it), each with its Kit part and words in both languages, its manifest entry, the Plan schema kind, the plan checks (PLAN-019), the assembler, the verifier's grounding, Kit tests, Python tests, and L6 rows.

**Next, by the same recipe:** a circuit for Ohm's law and parallel resistors, a wave for wave speed, a transformer, a decay curve with nuclei for half-life. One at a time, each green before the next.

**Out:** decoration that draws nothing measured.

## Exit criteria

- Each scene refuses to draw anything but its model (or the control that feeds it), at a scale the Plan checks and the verifier both accept.
- Every way a page can falsify the picture in the L6 rows is refused; the unmodified page is accepted.
- The two Plans verify in a real browser; their Malay translations still build.
