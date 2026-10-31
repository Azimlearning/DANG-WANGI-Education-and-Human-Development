#!/bin/sh
# Start the API on Render. DATA_DIR is the persistent disk (/data); the repo's own data is copied into it once, without overwriting anything that is there.
set -e
mkdir -p "${DATA_DIR:-/data}"
cp -rn /app/data-seed/. "${DATA_DIR:-/data}/"

# First start: build the library of stored labs (about 15 minutes, no model call). Nothing may be asked while it runs: a lab stored by a question first would clash
# with the same lab in the library (ConflictingRecord), so the server is not started until the library is whole.
if [ "${SEED_LIBRARY:-0}" = "1" ] && [ ! -f "${DATA_DIR:-/data}/environments.db" ]; then
  echo "seeding the library into ${DATA_DIR:-/data} (PUBLIC_ORIGIN=${PUBLIC_ORIGIN})"
  python -m api.library_seed --english-only
fi

# --proxy-headers: behind Render's proxy the client address comes from X-Forwarded-For, so the per-address limits count real visitors, not the proxy.
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
