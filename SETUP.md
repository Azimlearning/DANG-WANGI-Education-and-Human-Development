# Synapse v4: Local Setup Guide

How to run Synapse v4 on your own machine. Two servers run side by side: the **API** on port 8000 and the **web app** on port 3000.

By default everything runs on a deterministic fake model, so no API key is needed and nothing costs money.

---

## Quick start (already installed)

Open two terminals in the repository root and run one command in each.

**Terminal 1: API**

```bash
uv run uvicorn api.main:app --reload --port 8000
```

**Terminal 2: web app**

```bash
pnpm --filter web dev
```

Then open:

| What | URL |
|---|---|
| Web app (chat shell) | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| API health check | http://localhost:8000/health |

Both servers watch for code changes and reload on their own. Stop either one with `Ctrl+C`.

The web app needs the API. If the API is down, the chat shell loads but questions fail. Start the API first.

---

## First-time setup

### Requirements

| Tool | Version | Check with |
|---|---|---|
| Python | 3.13 | `python --version` |
| [uv](https://docs.astral.sh/uv) | 0.11 or newer | `uv --version` |
| Node | 24 (22 or newer works) | `node --version` |
| [pnpm](https://pnpm.io) | 10 | `pnpm --version` |

No Docker and no database server are needed. Local stores are SQLite files under `data/`.

### Steps

Run these from the repository root.

```bash
# 1. Python dependencies
uv sync

# 2. JavaScript dependencies (web, kit, schema)
pnpm install

# 3. Browser used by the verification harness
uv run playwright install chromium

# 4. Build the micro-component Kit (served at /vendor/kit/<semver>/)
pnpm --filter @synapse/kit build

# 5. Create your settings file
cp .env.example .env
```

On Windows PowerShell use `Copy-Item .env.example .env` for step 5.

Step 4 produces `packages/kit/dist/<semver>/`. Rebuild it after any change in `packages/kit/`.

---

## Settings (`.env`)

For local development you can leave the defaults. The ones that matter:

| Variable | Local value | Notes |
|---|---|---|
| `SYNAPSE_LLM_MODE` | `fake` | `fake` makes no network call and costs nothing. `live` is paid, needs `ANTHROPIC_API_KEY` and `LLM_MONTHLY_CAP_USD`, and the API refuses to start in `live` without them |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Where the web app finds the API. The web app also proxies `/vendor/*` to it |
| `PUBLIC_ORIGIN` | `http://localhost:3000` | The origin the web app is served from. The sandbox CSP names it explicitly |

Every variable, with where to get it, is in [`refdocs/guides/env_setup.md`](refdocs/guides/env_setup.md).

Never commit `.env`. It is gitignored. Never put `ANTHROPIC_API_KEY` in a `NEXT_PUBLIC_` variable.

---

## Verify it works

With both servers up:

```bash
curl http://localhost:8000/health
```

Then open http://localhost:3000, ask a Form 4 or 5 science question, and an Environment should appear in the sandbox with its citation and trust label.

Run the test suites (batch them rather than after every edit):

```bash
uv run pytest            # API tests
pnpm -r test             # web, kit and schema tests
```

Lint and types:

```bash
uv run ruff check api
uv run pyright api
pnpm -r lint
pnpm -r typecheck
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Address already in use` on port 8000 or 3000 | Another copy is still running. Find it with `netstat -ano \| findstr :8000` (or `:3000`) and stop that process, or pick another port (and update `NEXT_PUBLIC_API_BASE_URL` and `PUBLIC_ORIGIN` to match) |
| Web app loads but answers fail | The API is not running, or `NEXT_PUBLIC_API_BASE_URL` does not point at it. Restart the API first |
| Environment iframe is blank or scripts 404 | The Kit is not built. Run `pnpm --filter @synapse/kit build` and refresh |
| API refuses to start in `live` mode | `ANTHROPIC_API_KEY` or `LLM_MONTHLY_CAP_USD` is missing in `.env`. Set `SYNAPSE_LLM_MODE=fake` to go back to free mode |
| Verification or render errors mentioning a browser | Run `uv run playwright install chromium` |
| Changed `.env` but nothing changed | Restart the API. Settings are read at startup |
| Changed the textbook corpus (`CORPUS_DIR`) | Restart the API. The corpus is read once per process |

---

## Safety notes

- **Do not expose the API to the public internet.** There is no auth, and the rate limits are in-process and per worker (ADR D-11). The deploy gate is in [`refdocs/guides/checklist.md`](refdocs/guides/checklist.md).
- **Paid runs need the owner's go.** Setting `SYNAPSE_LLM_MODE=live` is not permission to run an evaluation, an ingestion or a generation sweep. State the projected cost first.
- The textbook corpus is never committed. Point `CORPUS_DIR` at a local folder if you have one.

---

## More

- [`README.md`](README.md): what the project is and the project layout
- [`refdocs/STATUS.md`](refdocs/STATUS.md): where the build is right now
- [`refdocs/guides/env_setup.md`](refdocs/guides/env_setup.md): every setting
- [`refdocs/guides/checklist.md`](refdocs/guides/checklist.md): pre-ship and deploy gate
