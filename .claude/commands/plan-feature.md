---
description: Write the plan + execution doc pair required before building
argument-hint: [what you want to build]
allowed-tools: Read, Write, Glob, Grep, Bash
---

Produce the plan/execution pair CLAUDE.md requires before any non-trivial implementation, for: $ARGUMENTS

First read `refdocs/STATUS.md`, the PRD, `refdocs/changelog/DECISIONS.md`, and the code this would touch. Check whether an existing plan already covers it. If so, say so instead of writing a duplicate.

Write two files, matching the structure of the existing docs in those directories:
- `refdocs/plans/YYYY-MM-DD-<slug>.md`: what and why: scope in/out with reasons, approach, a risk table with honest confidence levels, and a definition of done phrased as observable facts.
- `refdocs/execution/YYYY-MM-DD-<slug>.md`: how and in what order: numbered tasks, each naming the files it touches and carrying its own **Verify** step with a real command and expected result.

Where a task depends on an external library's behaviour, its first step is "read the actual docs/types/source". Do not encode an API you're recalling from memory.

If the feature touches a micro-component, a wire type, or a prompt pack, include the matching registration, codegen, or eval-delta step (preflight question 5) and name `kit-guardian` as the review step. If it includes a paid run, include a cost projection and an explicit "owner confirms the amount" step.

Do not implement anything. Return both paths and the task order.
