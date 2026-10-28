# Plan: W7b, five more models and the lab anatomy (the visual standard)

> Written 2026-10-27, after the owner's note that V4's output is below Synapse V3 and the demo video, and the build spec `brag-output-2026-10-21-195546/v4-video-feature-spec.md`. Execution: `refdocs/execution/2026-10-27-w7b-models-and-lab-anatomy.md`. Decisions: D-59, D-60, D-61.

## What and why

1. **Eight more science models and Plans** (backlog B8): relative atomic mass, energy value of a food, Boyle's law, effective resistance in parallel, buoyant force, cell voltage, population density by quadrat sampling, electrical energy. Four of them open topics with no Plan yet (Matter and the Atomic Structure, Digestive System and Digestion, Electrochemistry and Redox Reactions, Ecosystem).
2. **The visual standard** (spec section 2b): a lab takeover layout, one lab frame with one header row, the title once, the Kit page built as header, bench and panel (V3's anatomy), "My progress" in the top bar.
3. **Content gaps from the spec**: an exam item for the fermentation and five more, hints on the Hooke's law Plan and 24 others, the lab report's button and confirmation wording, the demo questions as quick starts.
4. **A question that names a lab** (spec item 5): library answers by name when the topic head is unsure.
5. **Left out, on purpose**: Bahasa Melayu (the owner's call of 2026-10-25; only reviewed strings may ship and no reviewer exists), the live code preview, the teacher dashboard, "Science checked" wording (all D-38 and D-39), the quadrat model (needs a relation the framework cannot say).

## Exit criteria

- 30 Environments verify in a real browser and are `kit-verified` with the corpus.
- The registration suite refuses every planted bug of every new model; L6 has no surprise miss and no false positive.
- At 1280 px after a question the lab pane is at least three quarters of the width, with one border between the pane and a Kit part and the title once; at 360 px there is no horizontal scroll and every control is 44 px.
- The sandbox is still exactly `allow-scripts`; no unverified page reaches the client.
