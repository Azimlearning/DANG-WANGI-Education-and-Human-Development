# Synapse v4

Turn a Malaysian Form 4 or 5 KSSM science question into a verified, interactive **environment**: raw HTML/JS assembled over a vetted library of micro-components (34 so far), with the textbook evidence and an honest trust label beside it.

**Status:** the pipeline runs end to end on deterministic fakes and produces 17 verified Environments across Physics, Biology and Chemistry. No paid model call has ever been made, and no textbook corpus is loaded. See [`refdocs/STATUS.md`](refdocs/STATUS.md) for exactly what is and is not done.

## What it does

A student asks a science question. Synapse routes it, finds the textbook passages that state what it is about, and builds an environment: a bounded interactive world (a simulation, an experiment bench, a process explorer, an exam-practice room) where a verified model of the science responds to what they do.

Three lanes decide how it is made and what it is allowed to claim:

- **Instantiate:** a stored, re-verified environment, or a template filled in. Seconds, almost no cost.
- **Compose:** the model writes raw HTML/JS that calls the micro-component Kit. Every displayed number must come from an audited science micro-model. Labelled `kit-verified`.
- **Free:** the model writes a whole document with no Kit. Labelled `model-checked`, never `canonical` without human review, and logged as a Kit gap.

Nothing unverified reaches the client: the deliverable type can only be minted by the verifier, and the delivery gate re-hashes it.

## Requirements

- Python 3.13 and [uv](https://docs.astral.sh/uv)
- Node 24 and [pnpm](https://pnpm.io) 10
- Playwright browsers for the verification harness (installed in P0 task 6)
- No Docker and no database server: stores are SQLite

## Setup

```bash
uv sync
pnpm install
cp .env.example .env
```

Settings are documented in [`refdocs/guides/env_setup.md`](refdocs/guides/env_setup.md). With no key and `SYNAPSE_LLM_MODE=fake` (the default) everything runs on a deterministic fake model at no cost.

## Usage

```bash
uv run uvicorn api.main:app --reload --port 8000
pnpm --filter web dev          # http://localhost:3000
pnpm --filter kit build        # builds the micro-component Kit
```

**Do not expose the API publicly.** There is no auth, and the limits that exist are in-process and per worker; see ADR D-11 and the deploy gate in [`refdocs/guides/checklist.md`](refdocs/guides/checklist.md).

## Project layout

The short version; [`refdocs/guides/file_map.md`](refdocs/guides/file_map.md) says what each file is for.

```
api/                 FastAPI: pipeline, verify (the trust path), evidence, llm seam, routing, models
  prompts/           prompt packs, versioned files
web/                 Next.js: chat shell, sandbox host, shared links, progress
packages/
  schema/            wire types (TypeScript), codegen to Pydantic
  kit/               micro-components and science models, bundle, manifest
eval/                golden, hostile, planted-defect, census, cost, parity fuzzer, browser smoke
data/                plans, catalogue, taxonomy, router data, fixtures (no textbook text)
refdocs/             the doc system: PRD, STATUS, plans, execution, changelog, decisions, evidence
.claude/             agents, commands, preflight, hooks
```

The textbook corpus is never in the repository: point `CORPUS_DIR` at a local folder.

## Documentation

| Doc | What's in it |
|---|---|
| [`refdocs/STATUS.md`](refdocs/STATUS.md) | Where the build actually is right now |
| [`refdocs/synapse-v4-PRD.md`](refdocs/synapse-v4-PRD.md) | Scope, architecture, roadmap, decision log |
| [`refdocs/brainstorm-2026-10-16.md`](refdocs/brainstorm-2026-10-16.md) | Founding research and brainstorm, with the interview amendment |
| [`refdocs/changelog/CHANGELOG.md`](refdocs/changelog/CHANGELOG.md) | Session-by-session history |
| [`refdocs/changelog/DECISIONS.md`](refdocs/changelog/DECISIONS.md) | Why things are the way they are |
| [`refdocs/guides/env_setup.md`](refdocs/guides/env_setup.md) | Every setting and where to get it |
| [`refdocs/guides/checklist.md`](refdocs/guides/checklist.md) | Pre-ship and deploy-gate checklist |
| [`refdocs/guides/file_map.md`](refdocs/guides/file_map.md) | Where everything is and what it is for |
| [`CLAUDE.md`](CLAUDE.md) | Operating brief for AI sessions on this repo |

## License

Not chosen yet. Decide before the repository is made public.
