# Execution: P2 on the real corpus

> Plan: `refdocs/plans/2026-10-18-p2-real-corpus-and-citations.md`. How and in what order. Keep this file true to what happened (CLAUDE.md rule 4).

## Where things live

| What | Where | In git |
|---|---|---|
| The owner's zip | `textbook-and-experiments-sample.zip` in the repo root (moved out by the owner when convenient) | **No** (`*.zip`, `*.pdf` ignored since 2026-10-18) |
| Unpacked PDFs | `C:\Users\User\synapse-corpus\raw\` | No |
| The text corpus | `C:\Users\User\synapse-corpus\text\` (`CORPUS_DIR` points here) | No |
| Quotations | `CORPUS_DIR\citations.json` (local) | **No** |
| Pointers (document, page, claim, who checked) and the corpus manifest | `data/citations/pointers.json`, `data/corpus_manifest.json` | Yes (no text) |

`C:\Users\User\synapse-corpus\corpus\` and `ingest.log` are from a first run that was stopped (long ids); they can be deleted.

## Tasks

| # | Task | Status |
|---|---|---|
| 1 | Unpack the zip outside the repo (path-checked); ignore `*.zip`, `*.pdf` in git | Done 2026-10-18 |
| 2 | Extend `api/evidence/ingest.py` (recursive, unique ids, per-page fault tolerance, resume, manifest with no text) with tests; add `pypdf` (BSD-3-Clause) and `fonttools` (MIT) to the `local` group | Done; 25 evidence tests pass |
| 3 | Ingest the 26 PDFs; record pages, empty pages, and fonts warnings per document | Done: 15 min; text layers present except 5 Chemistry experiment scans (159 pages) and a few stray pages; the font warnings went away after adding `fonttools` |
| 4 | OCR the pages with no text layer (the Chemistry experiment books); choose a tool, record its licence in `refdocs/synapse-v4-sources.md` | Not started. Not needed for the law citations (clean textbook pages); needed only for task 9. Candidates: Tesseract (Apache-2.0) via OCRmyPDF (MPL-2.0), or a pip-only RapidOCR (Apache-2.0) with pypdfium2 for rendering |
| 5 | Citation registry (`api/evidence/registry.py`): pointers plus local quotations, every quotation re-proved against the corpus; tests on synthetic data | Done (D-36); 9 registry tests |
| 6 | Wire the pipeline: resolve a Plan's `citation_ids`, mint `kit-verified` only if all prove, else `model-checked` with the UNVERIFIED placeholder and the reason in the trace; `eval/environments/build.py` and the API use it | Done: `api/pipeline/grounding.py` is shared; the API loads the corpus once per process |
| 7 | The Plans, one by one: find the page, check wording, units, scope and values, log each correction, add the citation | Done for 16 Plans: 6 corrections and 1 Plan moved out (cardiac output has no textbook basis); see the changelog |
| 8 | Rebuild the Environments with the corpus on; confirm the gate re-proves every citation; count `kit-verified` | Done: 16 of 16 `kit-verified`; also end to end through the API on fakes |
| 9 | Experiment catalogue matched to the owner's experiment documents (`confirmed_by_person` stays false) | Not started |
| 10 | Misconception list: look for each cited work (`source_verified` stays false unless a person confirms) | Not started |

## Rules for task 7

- The textbook wins over the Plan. If the Plan's formula, unit, scope or numbers disagree with the page, change the Plan (and its science model's reference if the Kit's value is wrong) or drop the Environment; never bend the quotation.
- A quotation is 25 to 400 characters, word for word, from a clean (non-OCR) page.
- A person reviews before any label above `kit-verified`. Nothing here sets `confirmed_by_person`.
- Every correction is one line in the changelog: what the Plan said, what the page says, what changed.
