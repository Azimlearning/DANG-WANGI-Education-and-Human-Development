# The Synapse API for a public demo (Render, see render.yaml and refdocs/guides/deploy_hackastone.md). Not tested with Docker on the author's machine (no Docker there):
# the first build on Render is the first test. The web app is NOT here; it goes on Vercel.

# 1. The Kit: the micro-component bundle the labs load from /vendor/kit/<semver>/. Kit 0.1.0 is unreleased and is relocked on each change (D-29), so the build relocks:
#    the library is seeded INSIDE the container (deploy/entrypoint.sh) against this bundle, so every stored lab agrees with it.
FROM node:24-slim AS kit
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/kit/package.json packages/kit/
COPY packages/schema/package.json packages/schema/
COPY web/package.json web/
RUN pnpm install --frozen-lockfile --filter @synapse/kit...
COPY packages/kit packages/kit
RUN pnpm --filter @synapse/kit build --relock

# 2. The API with Chromium (the verifier renders every generated lab in a real browser before a student sees it).
FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/app/.venv/bin:$PATH"
RUN playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
COPY api ./api
COPY eval ./eval
COPY conftest.py ./
# The API reads the repo's own data (Plans, fixtures, models, translations, citations) from /app/data, and the Kit's word list from its source. The stores (environments.db,
# ledger.db) live on the persistent disk, DATA_DIR=/data; the entrypoint also copies the repo data there once, never over a file already there.
COPY data ./data
COPY data /app/data-seed
COPY packages/kit/src/i18n.ts ./packages/kit/src/i18n.ts
COPY --from=kit /repo/packages/kit/dist ./packages/kit/dist
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
