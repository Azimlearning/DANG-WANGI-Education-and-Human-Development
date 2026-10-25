# Execution: cloud follow-ups (known constants, CI, citations, static gallery)

> Plan: `refdocs/plans/2026-10-25-p7-cloud-followups.md`. How and in what order. Keep this file true to what happened (CLAUDE.md rule 4).

## Working notes

- Work is on `main`, as the owner asked on 2026-10-25. The latest work (W0 to W4 stage 3) was pushed by the owner only to the `hackathon` remote; this clone's `origin/main` was at `ceb80cb`. The `hackathon` remote was added read-only and `main` fast-forwarded to `da09b47` before any code was written.
- The cloud container's preinstalled Chromium is build 1243; the pinned Python Playwright (1.56) wants build 1194 and cannot download it (proxy). A shim folder (`PLAYWRIGHT_BROWSERS_PATH`, outside the repo) links the headless shell to the expected layout. An environment workaround, not a repository change.
- No corpus in the cloud: every Environment built here is `model-checked`. That is not a regression.
- Bahasa Melayu is out of scope (owner, 2026-10-25).

## Tasks

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | Baseline on `da09b47`: install, Kit build (hash `fb33e0e7babf` equals the lock), codegen check, full suite | | see the changelog | Done |
| 2 | The constants table and PLAN-020 | `api/pipeline/{constants,plan_checks,failchecks}.py`, `test_plan_constants.py` | 7 new tests, plan and registry suites | Done |
| 3 | CI workflow (Kit and web, Python, smoke on Linux) | `.github/workflows/ci.yml` | YAML parsed; first real run is on GitHub | Done, unproved on GitHub |
| 4 | Friendly citations | `web/lib/citation.ts`, `web/components/Provenance.tsx`, `api/evidence/titles.py`, `api/export.py` | web 78 passed, `test_titles.py`, `test_export.py` | Done |
| 5 | Static gallery | `eval/gallery/build.py`, `test_gallery.py`, `eval/environments/build.py` (an `on_block` hook), `.gitignore` | 4 gallery tests including a file run in Chromium | Done |
