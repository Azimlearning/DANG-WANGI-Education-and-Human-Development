# Plan: W13, Malay questions for the router, and the trained-model GPU job

> Written 2026-10-27, after the owner asked for the trained model to be taken further ("u can do that if u want remember to use google collab there is a cli / mcp u cam use"). Execution: `refdocs/execution/2026-10-27-w13-malay-router-and-gpu-job.md`. Decision: D-63. Continues P1b (`2026-10-16-p1b-models-track.md`), whose deferred parts were a retrain on more data and an embedding comparison.

## What and why

W12 makes the labs readable in Bahasa Melayu. A student who reads Malay will also ask in Malay, and the router (TF-IDF and logistic regression, trained on English) was never measured on that. This workstream measures it, makes it safe and better with no training, and prepares the one thing that does need a GPU.

1. **Measure.** A 68-question probe set in Malay and mixed Malay and English, scored at the library's gate.
2. **Guard.** Recognise a Malay question, translate it with a glossary, and trust the local answer only if most of it was understood.
3. **GPU job.** Translate the router's training questions with NLLB-200 and fine-tune a multilingual encoder, to learn whether a dense model beats the guard (A-9, D-12).

## Scope

**In:** `api/models/malay.py` and its glossary; `routing.router.prepare` and `Route.english`; the library lookups on the translated question; `eval/models/bm_probe.py` and the probe file; `eval/models/colab/gpu_job.py`, its tests and README.

**Out, and why:** retraining the shippable router on Malay data (no translated data exists until the GPU job runs); an encoder inside the API (heavy dependency, D-20); answering in Malay (the explain prompt is English, and a prompt change needs an eval delta, rule 7); running the GPU job this session (see the execution doc).

## Exit criteria

- On the probe, with the guard: every question the library answers is answered correctly, and the share answered is more than twice what the English-only router gives.
- No English question of the 2,678 the router was built from is mistaken for Malay.
- The GPU job's pure parts are tested and its metrics equal the probe scorer's.
- The bar for adopting a dense model is written before the run, and the run's instructions work on a free GPU.
