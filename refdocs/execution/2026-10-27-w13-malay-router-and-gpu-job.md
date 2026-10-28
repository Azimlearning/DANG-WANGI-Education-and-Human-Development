# Execution: W13, Malay questions for the router, and the trained-model GPU job

> Plan: `refdocs/plans/2026-10-27-w13-malay-router-and-gpu-job.md`. Kept current while building (CLAUDE.md rule 4).

## Order of work

1. **Probe** (done): `data/models/router/bm_probe.jsonl`, 68 questions (53 Malay, 15 mixed), three or more per covered topic; `eval/models/bm_probe.py`.
2. **Guard** (done): `api/models/malay.py` (function-word detector, glossary, stemmer, coverage), `RouterModel.knows_word`, `routing.router.prepare`, `Route.english`, `run.py` uses it for name matching and the nearest Environment.
3. **GPU job** (written, not run): `eval/models/colab/gpu_job.py`, `test_gpu_job.py`, `README.md`.
4. **Retrain the shippable router on the translated Malay** (waits for step 3's files): add `--extra-train` to `eval/models/train_router.py`, retrain, recalibrate the gate, compare with the guard on the probe.

## Deviations and facts worth keeping

- **A wrong first reading.** The first run of the probe counted the router's `none` answers as library hits and reported "13 percent right, 91 percent answered, 8 percent right when answered". The router never trusts a local `none` (it goes to the fallback), so the scorer was wrong, not the router. Corrected numbers: English-only 19 percent answered (all right), topic accuracy 31 percent; with the guard 57 percent answered (all right), topic accuracy 78 percent.
- **Tools that could not be used.** The GPU job was written and its pure parts tested, but not run: the laptop has 188 MB free on C: and no GPU; Google's Colab CLI supports Linux and macOS only (WSL has no distribution installed, and installing one needs an administrator and a restart); the Kaggle connector answered "Unauthenticated" and its sign-in needs the owner. The Colab MCP server drives a notebook the owner has open.
- **Same author.** The glossary and the probe were written by the same assistant in one sitting, so the probe flatters the guard. The GPU job's translated test set and a person's questions are the checks that do not.
- **The glossary grew twice while writing the tests**: "panjang gelombang" (wavelength) was missing, and a long question with one function word was not detected as Malay. Both were found by the tests, not by tuning on the probe score.

## Verification ledger for this block

See the 2026-10-27 W12 and W13 row in `refdocs/STATUS.md`.
