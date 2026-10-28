# The W13 GPU job

What it answers: **does a trained multilingual encoder route Bahasa Melayu questions better than the glossary guard that ships today?** (D-63; the guard is `api/models/malay.py`.) It also writes the machine-translated Malay copy of the router's training questions, which a retrained TF-IDF router can use.

It is a measurement. The API never loads the encoder (it stays pure Python, D-20). Dense models join the pipeline only if measured to help (A-9, D-12), and the bar is written down before the run: the encoder must beat the guard's topic accuracy on `bm_probe.jsonl` by at least 5 points **and** keep `right_when_answered` at 1.0 on it. Otherwise the guard stays and the translated data is the only thing kept.

## What you need

- A free GPU: a Colab T4 or a Kaggle T4. The job needs about 6 GB of GPU memory and about 15 minutes. It costs no money.
- The data, all of which is safe to upload (LLM-written questions and the Malay probe; no textbook text, hard constraint 13): `data/models/router/{train,val,test}.jsonl` and `data/models/router/bm_probe.jsonl`.
- `eval/models/colab/gpu_job.py`.

## Where it can run, and what this laptop cannot do

- **This laptop (Windows, 188 MB free on C:, no GPU) cannot run it**: the two models are about 2.5 GB. The tests of its pure parts run anywhere (`uv run pytest eval/models/colab`).
- **Colab CLI** (`uv tool install google-colab-cli`, `colab run --gpu T4 gpu_job.py ...`): Google's README says Linux and macOS only, and it logs in with a Google account in a browser. Use it from WSL or another machine.
- **Colab MCP server**: it drives a notebook you have open in your browser; it needs your session.
- **Kaggle** (free T4 or P100, about 30 GPU hours a week): create a private dataset from the four files, create a notebook with the GPU on and internet on, add a cell `!pip -q install transformers` and `!python gpu_job.py --data /kaggle/input/<dataset> --out /kaggle/working/out`, then download `report.json` and the three `*_ms.jsonl` files. The Kaggle MCP in this project's setup needs you to sign in (`/mcp`) before an agent can do it for you.
- **Colab in the browser**: upload the files, a cell `!pip -q install transformers`, a cell `!python gpu_job.py --data /content/data --out /content/out`.

## What comes back, and what to do with it

`report.json` has, for the encoder, the topic accuracy, the share answered from the library and the share of those that were right, on the English test set, the machine-translated Malay test set and the hand-written probe. Put it next to `uv run python -m eval.models.bm_probe` (the guard) and decide by the bar above. Record the result in `refdocs/evidence/` and in `refdocs/changelog/CHANGELOG.md`.

The translated files are noisy machine translation. They are good for training a router to recognise Malay words and poor as a reference for how a student writes; the probe, written by hand, is the honest number.
