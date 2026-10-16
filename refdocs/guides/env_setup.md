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
| `STORE_ATTESTATION_KEY` | none | A secret string (32 or more random characters) that signs every stored Environment (HMAC-SHA256, A-19). Keep it OUTSIDE the data directory and out of git. Set: the delivery gate refuses any row without a valid signature, so a row written straight into the SQLite file is never delivered. Unset: rows are unsigned and the gate trusts the store (acceptable only while the API is single-operator and not public, D-11). Required at the deploy gate. Changing it makes every older row `unattested`, so re-verify after a rotation |
| `RATE_LIMIT_PER_MINUTE` | `20` | Questions one client address may ask per minute; above it `/ask` answers HTTP 429 `rate_limited`. `0` turns it off. Behind a proxy every client shares the proxy's address, so set the limit at the proxy as well. Not a secret |
| `MAX_CONCURRENT_ASKS` | `3` | How many questions are worked on at once (each may launch a browser to verify an Environment, so this bounds memory and CPU). Above it `/ask` answers 429. `0` turns it off. Not a secret |
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
