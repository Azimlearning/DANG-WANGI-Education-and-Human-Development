version: 1
purpose: ask the planner once more with the named issues from the checks
tier: standard
inputs: issues
budget: 500
cache: stable
---
Your previous Plan was refused by Synapse's checks. Fix exactly these problems and change nothing else. Reply with the corrected JSON object only.
=== VARIABLE ===
{{issues}}
