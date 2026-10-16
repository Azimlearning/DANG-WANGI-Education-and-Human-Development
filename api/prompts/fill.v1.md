version: 1
purpose: write one small custom slot for a page the assembler already built
tier: light
inputs: slot, purpose, allowed_calls, names, max_lines, issues
budget: 700
cache: stable
---
Task: write the few lines of JavaScript for one custom slot of a page that already exists. The slot is named below.

The page's sliders, models and readouts are already built. Your lines run after them. You may use only the names listed below and call only the Kit components listed below.
Do not use network, storage, timers, navigation, eval, markup or any name that is not listed. Numbers in sentences must be slider values, constants or model parameters.
Reply with the JavaScript only, no explanation, no code fences.
=== VARIABLE ===
Slot: "{{slot}}". Purpose: {{purpose}}
Names you may use: {{names}}.
Kit components you may call: {{allowed_calls}}. Write at most {{max_lines}} lines.

{{issues}}
