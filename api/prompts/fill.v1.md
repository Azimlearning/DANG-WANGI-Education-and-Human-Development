version: 1
purpose: write one small custom slot for a page the assembler already built
tier: light
inputs: slot, purpose, allowed_calls, names, max_lines, issues
budget: 700
cache: stable
---
Task: write the few lines of JavaScript for the custom slot "{{slot}}". Purpose: {{purpose}}

The page already exists. Your lines run after its sliders, models and readouts. You may use only these names: {{names}}.
You may call only these Kit components: {{allowed_calls}}. Write at most {{max_lines}} lines.
Do not use network, storage, timers, navigation, eval, markup or any name that is not listed. Numbers in sentences must be slider values, constants or model parameters.
Reply with the JavaScript only, no explanation, no code fences.

{{issues}}
