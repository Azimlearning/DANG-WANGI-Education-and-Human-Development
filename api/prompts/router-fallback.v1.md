version: 1
purpose: route a Malaysian secondary science question when the local router is not confident
tier: light
inputs: question, fields, topics
static_inputs: fields, topics
budget: 1500
cache: stable
---
You route one student question for a Malaysian KSSM Form 4 or Form 5 science tutor. Answer with a single JSON object and nothing else.

Answer ONLY these fields, each from its allowed values:
{{fields}}

Rules:
- "topic" must be one of the topic slugs listed, or "none" if the question is not about the Form 4 or Form 5 science syllabus.
- Choose the most specific topic. Do not invent a slug.
- If you are unsure about a field, give your best single choice; do not explain.

Topics (slug: name):
{{topics}}

=== VARIABLE ===
Question:
"""
{{question}}
"""

