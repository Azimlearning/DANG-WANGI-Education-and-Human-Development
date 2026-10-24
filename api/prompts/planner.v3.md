version: 3
purpose: turn a routed question into a validated Plan (data, no code)
tier: standard
inputs: schema, pattern_pack, kit_pack, exemplar, question, route, issues
static_inputs: schema, pattern_pack
budget: 3200
cache: stable
schema: schemas/plan.schema.json
---
Task: write the Plan for one interactive Environment that answers the student's question.

A Plan is data. It names sliders with ranges, science models with parameters, readouts, and the short words around them. Code is assembled from it by Synapse.

How to plan:
- Pick the one model in the Kit that matches the question. Set its parameters to values a textbook would use, inside the model's domain.
- A model line in the Kit list ends "in a Plan:" with the exact id for "model", its input names and its param names. Copy the id exactly. Each input is bound to a slider or constant; each param is a fixed number you set. Never invent an id: if no listed model fits, pick the closest listed one.
- Sliders: one per quantity the student should vary, with a range that makes the pattern easy to see and stays inside the model's domain. Give each a starting value inside its range and a grid (the number of equal intervals to test).
- Bind each model input to a slider or constant of the same unit.
- Readouts: show what the model returns, in its unit (or a conversion the Kit knows).
- Words: a short study note (what the law says), at most a few sentences, and steps if the pattern needs them. Only use numbers that are slider values, grid positions, constants or model parameters.
- Keep it small. Fewer parts that work beat many parts.

Pattern guidance:
{{pattern_pack}}

Schema (reply with JSON that matches it):
{{schema}}

=== VARIABLE ===
Components available (use only these):
{{kit_pack}}

Nearest worked example (for shape only; do not copy its science):
{{exemplar}}

Routing for this question: {{route}}

Student's question:
"""
{{question}}
"""

{{issues}}
