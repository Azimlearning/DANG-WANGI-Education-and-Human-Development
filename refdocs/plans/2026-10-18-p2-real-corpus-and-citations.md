# Plan: P2 on the real corpus (Step 2 of the local handoff)

> Execution doc: `refdocs/execution/2026-10-18-p2-real-corpus-and-citations.md`. Phase P2 of `refdocs/synapse-v4-PRD.md` section 6, finished locally because the corpus cannot be in the cloud (D-14, A-8).

## Why this exists

All 17 Environments are `model-checked` with an UNVERIFIED citation: nothing has ever confirmed a formula, unit, wording or scope against a textbook. The mint and the gate can already grant `kit-verified` to an Environment whose every citation is a quotation the local corpus can find word for word (D-25), but that path has only ever been proved against a synthetic corpus, and the pipeline cannot use it: a Plan carries only empty `citation_ids`, and `api/pipeline/run.py` always mints `model-checked` with the single UNVERIFIED placeholder.

The owner supplied the textbooks and sample experiment documents on 2026-10-18 (26 PDFs, 1.3 GB, English and Malay, Physics, Chemistry and Biology Form 4 and 5). This plan turns them into a corpus, finds the page that states each Plan's law, and wires real citations through.

## What's already covered

| Need | Where |
|---|---|
| Corpus format, BM25 search, exact-after-normalisation `verify_quote` | `api/evidence/corpus.py` (D-25) |
| A verified citation or none | `api/evidence/citations.py` (`cite`, `Evidence`) |
| `kit-verified` only if every citation is re-proved; the gate repeats it | `api/verify/mint.py` `guard_label`, `api/verify/gate.py` |
| PDF to corpus | `api/evidence/ingest.py` (extended 2026-10-18: recursive, unique ids, manifest, resume) |

## Scope

**In:**
1. The corpus: ingest the 26 PDFs into a local folder outside every repository; OCR the pages that have no text layer; a manifest with hashes and page counts (committed, no text).
2. A citation registry that keeps **quotations out of the repository** (rule 13; A-8 covers local use, not publication). The repo holds pointers only (`data/citations/pointers.json`: citation id, document, PDF page, the claim it supports, who checked). The quotation itself lives beside the corpus (`CORPUS_DIR/citations.json`) and is re-proved against the corpus text every time it is used.
3. The pipeline: resolve a Plan's `citation_ids` through the registry; when every citation proves, mint with those citations and the label `kit-verified`; when any does not, say so in the trace and mint `model-checked` with the UNVERIFIED placeholder, never higher (hard constraint 4).
4. For each of the 17 golden Plans: find the textbook page that states the law, read the Plan's wording, units, scope and values against it, fix or drop what does not match (each correction logged), add the citation.
5. The experiment catalogue: match `data/experiments/catalogue.json` to the owner's experiment documents; `confirmed_by_person` stays false until a person checks.
6. The misconception list citations (`source_verified` is false on all five).

**Out (and why):**
- Any label above `kit-verified` (`reviewed`, `canonical`): needs a person (hard constraint 3).
- Quoting the textbooks in anything public, and committing any quotation: the owner has not confirmed A-8 for publication. Held to the deploy gate.
- Dense retrieval over the corpus: only if measured to help (D-12, A-9).
- Reading the Malay editions against the English ones for translation: that is P7.

## Design

- **Document id** is a slug of the PDF's path under the source folder, so the Ministry's two editions and the repeated experiment files do not collide. A citation names a document id and a **PDF page index** (1-based), which is not always the printed page; the registry records both when known.
- **A citation is a claim a person can check.** The pointer file says which statement of the Plan each citation supports ("the extension is proportional to the load, within the elastic limit"), so a reviewer opens the page and compares.
- **Fail closed, say why.** An unresolved id, a document missing from the corpus, a page without text, or a quotation not found: the Environment is `model-checked` and the trace names the id and the reason. Nothing is guessed.
- **No fuzzy matching.** A quotation is exact after normalisation (case, spacing, hyphenation, quote marks). An OCR error in the corpus breaks a citation visibly; the fix is to choose a clean passage, not to loosen the match.

## Risks and open questions

- **ASSUMED (A-8):** local use is allowed and brief cited quotation is acceptable. Publication is unconfirmed; the registry design keeps the repository clean either way.
- **The textbooks are the "worked answer" the oracle bet (A-5) relies on.** If a Plan's formula differs from the book's, the book wins and the Plan changes, or the Plan is dropped.
- **Some textbooks may be scans.** OCR quality limits what can be quoted exactly. Four Chemistry experiment books were known to be image-only; the zip's copies are probed in the first execution task.
- **PDF page index vs printed page.** The student sees the citation; the printed page is friendlier. Store both where known.
