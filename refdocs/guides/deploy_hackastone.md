# Deploying Synapse v4 for the Hackastone grand final

> Written 2026-10-29 for the owner. Two pieces: the **web app on Vercel** and the **API on Render** (a container with Chromium). Vercel cannot run the API (Chromium, a SQLite store, long streaming answers). The files here (`Dockerfile`, `render.yaml`, `deploy/entrypoint.sh`) have **not been run with Docker**; the first Render build is their first test. The owner waived the deploy gate for this demo (D-75): read "What is still open" before the presentation.

## Order matters: the web URL comes first

Every lab is verified for ONE web origin (its CSP names it), so the library must be built for the final Vercel URL. So: create the Vercel project first, note its production URL, then deploy the API with that URL.

### 1. Vercel (the web app)

1. vercel.com > Add New > Project > import `Azimlearning/Synapse-v4` (private; Vercel needs access to it).
2. **Root Directory: `web`**. Keep "Include source files outside of the Root Directory" on (the app imports `packages/schema`). Framework: Next.js (detected). The default pnpm install and `next build` are right; `pnpm --filter web build` was run locally and passes.
3. Environment variable (Production): `NEXT_PUBLIC_API_BASE_URL` = the Render API URL, no trailing slash (you get it in step 2; set a placeholder now and redeploy after).
4. Deploy. Note the **production** URL (for example `https://synapse-v4.vercel.app`). Use only this URL for the demo: the API allows exactly one origin, so preview URLs are refused.

### 2. Render (the API)

1. dashboard.render.com > New > Blueprint > pick the repo. It reads `render.yaml`: a Docker web service `synapse-api`, plan **Standard** (2 GB; Chromium needs it; about $25 a month, billed by the hour, so delete it after the final), a 1 GB disk at `/data`, region Singapore.
2. It asks for the two values marked `sync: false`: `ANTHROPIC_API_KEY` (paste your key; it is never in the repo) and `PUBLIC_ORIGIN` (the Vercel production URL from step 1, no trailing slash).
3. First boot builds the library (`SEED_LIBRARY=1`, about 15 minutes, no model call) and only then starts the server. Do not ask anything meanwhile. Later boots skip it because `/data/environments.db` exists. If `PUBLIC_ORIGIN` ever changes, delete `/data/environments.db` (Render shell) and restart so the library is rebuilt for the new origin.
4. Check `https://<your-api>.onrender.com/health`: it must say `"llm_mode":"live"`.
5. Put that API URL into Vercel's `NEXT_PUBLIC_API_BASE_URL` and redeploy the web app.

### The textbook corpus (your call, A-8)

The corpus is not in the repo and is not in the image. Without it nothing can earn **Kit verified** (a citation must be found word for word in the book): every lab shows **model-checked** instead, which looks weaker to judges. To get the same labels you see locally, upload the corpus text to the disk (`/data/corpus`) from the Render shell and set `CORPUS_DIR=/data/corpus` before the first boot. That puts the textbook text on a server you control (it is never sent to visitors beyond short cited quotes), which is the open question A-8: decide it before you do it.

## What the owner chose (D-75)

- API on Render; live mode for everyone; the **$4 monthly cap** is the only hard spend limit. The per-address limits (`DAILY_LIMIT_PER_CLIENT` 30, `DAILY_LIMIT_TOTAL` 150, 2 questions at once) slow a crowd but there are no accounts.
- Library labs cost nothing. A question outside the library costs about $0.08 (W16 measurement), so **$4 minus the $1.37 already spent is about 30 new labs for the whole month**. Raise `LLM_MONTHLY_CAP_USD` in Render if the presentation may need more, and say how much you accept.

## What is still open (the deploy gate, `checklist.md`)

Not met, and waived for the demo by the owner: generated HTML is not verified in a no-network container with resource limits; no `security-reviewer` pass; no licence; the name question (A-14); the corpus position (A-8); no real-phone pass; per-address limits are in-process per worker. Nothing here is a claim that the gate is met.

## Before the presentation

- Open the Vercel URL on a phone and on the laptop; ask one library question and one new question; watch the progress bar finish.
- Render's Standard plan does not sleep, but redeploys restart the container: do not deploy within the hour before the demo.
- Have a screen recording ready as a fallback.
