# Environment Setup: Synapse v4

> **Security:** never commit a real value from this file. `.env*` is gitignored; `.env.example` carries the *names* with blank values and is committed.
> Never paste a real token into a plan, an execution doc, a changelog entry, or a chat transcript. If one leaks, rotate it: don't just delete the message.
> **Naming:** this file is about process settings (the `.env` file). It has nothing to do with the "Environment" artifact Synapse generates.

Last updated: 2026-10-16

---

## Required variables

| Variable | Required | Where to get it | Read by | Notes |
|---|---|---|---|---|
| `SYNAPSE_LLM_MODE` | Yes (defaults to `fake`) | Set by you: `fake` or `live` | API | `fake` uses a deterministic fake model and makes no network call. `live` is paid and needs the two rows below |
| `LLM_MONTHLY_CAP_USD` | Yes in `live` mode | Set by you, in US dollars | API LLM seam | Calls are refused before sending if they would exceed it. The API refuses to start in `live` mode without it |
| `ANTHROPIC_API_KEY` | Yes in `live` mode | https://console.anthropic.com (API keys) | API | Server side only. Never `NEXT_PUBLIC_` |
| `NEXT_PUBLIC_API_BASE_URL` | Yes for the web app | Your API address, `http://localhost:8000` locally | Web | Public by design: it is a URL, not a secret |
| `PUBLIC_ORIGIN` | Yes | The origin the web app is served from, `http://localhost:3000` locally | API (CSP injection) | The artifact CSP names this origin explicitly (ADR D-06) |

## Optional variables

| Variable | Default if unset | What it changes |
|---|---|---|
| `OPENROUTER_API_KEY` | none | Enables an OpenRouter fallback route when Anthropic is unavailable or out of credit |
| `KIT_DIST_DIR` | `./packages/kit/dist` | Where the built Kit lives (`<semver>/core.js`, `manifest.json`). The API serves it at `/vendor/kit/` and the render harness reads it. Build it with `pnpm --filter @synapse/kit build` |
| `VERIFY_INTERACTION_SECONDS` | `10` | How long the render harness presses controls and inputs while verifying one Environment (the longer, the more conditional behaviour it can reach). Tests use `1`. Not a secret |
| `CORPUS_DIR` | none | A local folder of textbook text (one `.jsonl` per document, made by `api/evidence/ingest.py`). Never committed (rule 13). Unset means no citation can be verified, so `kit-verified` cannot be minted. Not a secret, but the contents are copyrighted |
| `DATA_DIR` | `./data` | Where local stores and the default spend ledger live |
| `LEDGER_PATH` | `<DATA_DIR>/ledger.db` | Overrides the spend ledger file. Keep ONE ledger so the monthly cap covers every run |
| `LOG_LEVEL` | `INFO` | API log verbosity |

---

## Setup

```bash
# Not runnable until P0 task 1 creates the workspace.
cp .env.example .env
# Edit .env. For development leave SYNAPSE_LLM_MODE=fake and no key is needed.
```

Surface notes: the API reads everything except `NEXT_PUBLIC_API_BASE_URL`. The web app reads only `NEXT_PUBLIC_*`. The web build must never see `ANTHROPIC_API_KEY`.

---

## Rules

- **Client-side bundles are public.** Anything inlined into a browser build is readable by anyone who opens devtools. A key that must stay secret goes through a server-side route, never into client code.
- **`.env.example` is the documentation.** Add the variable name there the moment you add the variable.
- **A missing required variable should fail loudly at startup**, with a message naming the variable and pointing here.
- **Rotate on exposure, not on suspicion of exposure.** If you can't prove a key never left the machine, treat it as leaked.
- **Paid runs need the owner's go.** Setting `SYNAPSE_LLM_MODE=live` is not permission to run an evaluation or an ingestion. State the projected amount first (CLAUDE.md rule 7).

## When a variable changes

Adding, renaming, or removing one means updating, in the same session: this file, `.env.example`, the deploy target's dashboard (if any), and a changelog entry.
