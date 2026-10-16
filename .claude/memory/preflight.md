# Preflight: Synapse v4 Session Start

> Read this at the start of every session, before touching code.
> One page, six questions, then you can build. CLAUDE.md is the reference; this is the gate.

---

## 1. Where are we?

Open `refdocs/STATUS.md`. Find the current phase and the one next action.
If STATUS's claims and the code disagree, **that's the session's first task**, not the thing you were about to do.

---

## 2. Which surface am I about to touch?

| Surface | Root | Shares source with the others only through |
|---|---|---|
| API | `api/` | `packages/schema` (generated Pydantic) and the Kit manifest (JSON) |
| Web | `web/` | `packages/schema` (types) and `/vendor/kit/<semver>/` (static files) |
| Kit | `packages/kit/` | its generated `dist/<semver>/` bundle and `manifest.json` |
| Schema | `packages/schema/` | nothing: it is the source |

`api/` and `web/` never import each other. A change in one surface does not reach another until its generated artefact is rebuilt. Never edit two surfaces in the same session without tracking both in the changelog.

---

## 3. Does a plan exist for what I'm about to build?

Non-trivial feature: a plan doc in `refdocs/plans/` **and** an execution doc in `refdocs/execution/`.
If neither exists, write them first (`/plan-feature`). If one exists but reality has moved, update it before building on it.

---

## 4. Has this already been decided?

Skim `refdocs/changelog/DECISIONS.md` before re-opening an architectural choice. If your plan contradicts an ADR, you need a new ADR that says why, not a silent reversal.

Check the open `ASSUMED:` list (PRD section 8). If today's work is load-bearing on one of them, **confirm it before you build**, not after. The ones that bite first: the oracle (A-5), the Kit API (A-2), isolation (A-10), exposure (A-11), corpus legality (A-8).

---

## 5. If I changed a wire type or a micro-component, did the matching change land?

This is the rule that breaks silently: the first half compiles and passes its own tests.

- **Wire type** (`packages/schema`): did `pnpm codegen` run and does `pnpm codegen:check` pass? Does the web registry handle the new block and all its render states? Is the Python model strict and fail closed?
- **Micro-component** (`packages/kit`): is there a manifest signature, a written precondition, a prompt-sized doc, an accessibility fence, and a registration suite of planted defects that all get refused? For a **science** micro-model: a textbook citation, units and domain, an independent hand-written reference (not derived from the implementation), properties? Did a behaviour change bump the Kit semver so stored environments go stale?
- **Prompt pack** (`api/prompts/`): did the version bump and is an eval delta recorded?

Enforcement today is `pnpm codegen:check`, the Kit registration suites and `kit-guardian`. There is no hook for this yet; write one the first time the rule is broken.

---

## 6. Will I close the session properly?

`/session-end`: changelog entry, STATUS phase table, verification ledger, any new ADR.
The changelog entry is mandatory after any session that changed code, made a decision, or modified a plan. Even a one-line fix gets a one-line entry.

If any paid call is on the path: state the projected amount and wait for the owner's go (CLAUDE.md rule 7).

---

## Quick links

| Doc | Purpose |
|---|---|
| `refdocs/STATUS.md` | Where the build actually is |
| `CLAUDE.md` | Operating brief: rules, constraints, stack |
| `refdocs/synapse-v4-PRD.md` | Scope, architecture, roadmap, decision log |
| `refdocs/changelog/DECISIONS.md` | Settled calls: read before re-debating |
| `refdocs/guides/env_setup.md` | Every setting, where to get it |
| `refdocs/guides/checklist.md` | Pre-ship and deploy-gate checklist |
| `refdocs/plans/` and `refdocs/execution/` | What and why, how and in what order |
