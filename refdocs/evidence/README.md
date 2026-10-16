# Evidence

> Measurements and estimates the project's decisions rest on. Each file says plainly which it is. Nothing here is a claim of coverage or correctness unless it names the command that produced it.

| File | What it is | Kind | Status |
|---|---|---|---|
| [2026-10-16-p0-census.md](2026-10-16-p0-census.md) | The P0 coverage census: 53 KSSM topics against the Kit's micro-component kinds, with counts and a first-vertical ranking | **Estimate** (one annotator, from topic names and hints, no textbook opened) | Awaiting the owner's review |

| [2026-10-16-chatgpt-ui-research.md](2026-10-16-chatgpt-ui-research.md) | How ChatGPT's apps UI works (Apps SDK, MCP Apps, A2UI, AG-UI) and what it means for the Mark 3 pipeline | **Research from search summaries**, not primary pages; lists the pages to read locally | Done |

The census file is generated: edit `eval/census/census.py`, then run `uv run python eval/census/census.py --write-report`. A test fails if the file is stale. The topic list is `data/kssm_topics.json`, ported from Synapse v3 with its provenance recorded in the file.
