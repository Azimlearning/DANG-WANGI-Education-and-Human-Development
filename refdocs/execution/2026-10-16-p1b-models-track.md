# Execution: P1b Models track

> Plan: `refdocs/plans/2026-10-16-p1b-models-track.md`. A task is not done until its Verify passes. If reality diverges, edit this doc.

## Before starting

- Read D-20. The source data is the GenUI-Education clone at `/home/user/azimlearning/genui-education` (read-only). Locally, clone it or copy the dataset folder and set `ROUTER_DATA_DIR`.
- `uv add --group ml scikit-learn numpy`. These are training-time only; the API's runtime stays free of them.
- No paid call. No network at inference.

## Task 1: Dataset module and audit

**Files:** `eval/models/data.py`, `data/models/README.md`, `data/models/router/{train,val,test}.jsonl` (derived, small), `eval/models/test_data.py`.

**Steps:**
1. Read `clean/train.jsonl`, `clean/test.jsonl` and the labeled files in full, with provenance in a header comment (repo, commit, path).
2. Normalise labels. Keep current-taxonomy `curriculum_topic` tags; map missing tags to `none`; drop stale tags and count them. Report class counts per head.
3. Audit duplicates and near-duplicates (normalised text) inside train, and between train and test. Remove leaked rows from train, never from test.
4. Split a stratified validation set from train with a fixed seed. Write the derived files and an audit report.

**Verify:** `uv run pytest eval/models/test_data.py -q`: no query in both train and test; counts add up; every topic label is in the taxonomy or `none`; the audit numbers are reproducible.

## Task 2: Baselines

**Files:** `eval/models/baselines.py`, tests.

**Steps:** a majority-class predictor per head; a keyword rule that scores each topic by overlap of the question's tokens with the topic's label and hint tokens, and picks a domain from its subject.

**Verify:** tests with fixed expectations; the baselines run on the test split and print accuracy and macro-F1.

## Task 3: Train the multi-head router

**Files:** `eval/models/train_router.py`, tests.

**Steps:** word 1 to 2 gram and character 3 to 5 gram TF-IDF, one logistic regression per head, class-balanced weights, fixed seeds, regularisation picked on validation. Report accuracy, macro-F1 and a bootstrap interval on the held-out test for each head and each baseline.

**Verify:** the run prints the comparison table; the model beats the majority baseline on every head (otherwise the head is marked unused).

## Task 4: Export and pure-Python inference

**Files:** `api/models/{artifact,router_model}.py`, `api/models/artifacts/router-v1.json` (or a gitignored build if too large), tests.

**Steps:** export vocabulary, idf, sparse weights and label lists with the feature settings and a content hash. Implement the same featuriser and the linear scoring in pure Python. If the artifact is over about 1.5 MB, prune near-zero weights and measure the accuracy cost, or build it on demand and gitignore it.

**Verify:** parity test: pure-Python predictions equal scikit-learn's on every test row; training twice yields identical bytes.

## Task 5: Confidence gate, calibration and the model card

**Files:** `eval/models/calibrate.py`, `refdocs/evidence/2026-10-16-p1b-router-model-card.md` (generated), tests.

**Steps:** pick, per head, the lowest threshold on validation data that reaches the target accuracy on accepted questions; report coverage and accuracy at that threshold on test. Write the card: provenance, metrics against baselines with intervals, the teacher-noise limit, failure examples, how to retrain, what it must not be used for.

**Verify:** the card is generated and a test fails if it is stale; a head whose gate gives under 20 percent coverage is marked "not useful as a gate".

## Task 6: Router and the misconception matcher

**Files:** `api/routing/router.py`, `api/routing/fallback.py`, `api/models/misconceptions.py`, `data/misconceptions.json`, tests.

**Steps:** `route(question)` returns the topic, domain, pattern, complexity, a confidence and a source (`local` or `llm_fallback`); below the head's threshold it calls the fallback through the LLM seam (a deterministic fake in development). Port the v1 misconception list with provenance and match questions by BM25 over statements and triggers.

**Verify:** tests prove no network use, correct gating, the fallback being called exactly when below threshold, and the matcher finding each seed entry from its own statement. The card and the matcher both say the matcher's accuracy is unmeasured.

## Task 7: Wrap-up

- STATUS (phase table, ledger), CHANGELOG, DECISIONS, indexes, the Deferred to local register (embedding comparison; retrain on the full local dataset).

## As built (reconciled 2026-10-16)

- All seven tasks done in the cloud. Files differ slightly from the plan: `api/models/{features,router_model,gate,misconceptions}.py` (features and gate added), `eval/models/calibrate.py` writes both the gate file (`api/models/artifacts/router-v1.gate.json`) and the card, and `data/models/router/{metrics,parity,audit}.json` are generated.
- Features: word 1 to 2 gram (min_df 2) and character 3 to 5 gram (min_df 5) TF-IDF; weights below 0.1 dropped and rounded to 4 places, so the artifact is 2.7 MB (plan guessed 1.5 MB); every reported number is for that shipped model.
- The fallback prompt pack is the first file in `api/prompts/` and the loader enforces versioned files.
- The retrain-twice-identical test is behind `RUN_SLOW=1` (it takes about four minutes); the two manual runs gave the same hash.
- Misconception citations are v1's and stay `source_verified: false`.
