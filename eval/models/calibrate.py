"""Pick each head's confidence threshold on validation data, report what it buys on the held-out test, and write the model card.

    uv run python eval/models/calibrate.py            # writes api/models/artifacts/router-v1.gate.json and the model card
    uv run python eval/models/calibrate.py --check    # exits 1 if either file is out of date with the artifact and metrics

Provenance: new in v4. Uses only the pure-Python model, so it also exercises the shipped inference path. Free to run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.models import router_model  # noqa: E402
from eval.models.data import DERIVED, HEADS, SOURCE_COMMIT, load_split  # noqa: E402

GATE = REPO / "api" / "models" / "artifacts" / "router-v1.gate.json"
CARD = REPO / "refdocs" / "evidence" / "2026-10-16-p1b-router-model-card.md"
TARGET = 0.90  # accuracy wanted on the questions the model answers by itself
MIN_COVERAGE = 0.20  # below this the gate sends nearly everything to the LLM and the head is not useful as a gate


def labelled(rows: list[dict], head: str) -> list[dict]:
    return [r for r in rows if r[head] is not None]


def predictions(model: router_model.RouterModel, rows: list[dict], head: str) -> list[tuple[object, float, object]]:
    return [(model.predict(r["query"])[head].label, model.predict(r["query"])[head].confidence, r[head]) for r in rows]


def at(threshold: float, preds: list[tuple[object, float, object]]) -> tuple[float, float]:
    kept = [(p, t) for p, c, t in preds if c >= threshold]
    if not kept:
        return 0.0, 0.0
    return len(kept) / len(preds), sum(str(p) == str(t) for p, t in kept) / len(kept)


def choose(preds: list[tuple[object, float, object]]) -> float | None:
    """The lowest threshold whose accepted validation questions reach TARGET accuracy with at least MIN_COVERAGE, else None."""
    for threshold in sorted({round(c, 3) for _, c, _ in preds}):
        coverage, accuracy = at(threshold, preds)
        if coverage >= MIN_COVERAGE and accuracy >= TARGET:
            return threshold
    return None


def build() -> tuple[dict, list[dict]]:
    model = router_model.load()
    val, test = load_split("val"), load_split("test")
    gate: dict = {"artifact_sha256": model.sha256, "target_accuracy": TARGET, "min_coverage": MIN_COVERAGE, "heads": {}}
    failures: list[dict] = []
    for head in HEADS:
        v = predictions(model, labelled(val, head), head)
        t_rows = labelled(test, head)
        t = predictions(model, t_rows, head)
        threshold = choose(v)
        entry: dict = {"threshold": threshold, "useful": threshold is not None}
        if threshold is not None:
            vc, va = at(threshold, v)
            tc, ta = at(threshold, t)
            entry |= {
                "val_coverage": round(vc, 4),
                "val_accuracy": round(va, 4),
                "test_coverage": round(tc, 4),
                "test_accuracy": round(ta, 4),
            }
        else:
            best = max(
                ((at(th, v), th) for th in sorted({round(c, 3) for _, c, _ in v})),
                key=lambda x: (x[0][1] >= TARGET, x[0][0]),
            )
            entry["best_val_coverage_at_any_threshold"] = round(best[0][0], 4)
        gate["heads"][head] = entry
        if head == "topic":
            wrong = [
                (r["query"], p, c, r[head]) for r, (p, c, _) in zip(t_rows, t, strict=True) if str(p) != str(r[head])
            ]
            wrong.sort(key=lambda x: -x[2])
            failures = [
                {"query": q, "predicted": p, "confidence": round(c, 3), "teacher": tr} for q, p, c, tr in wrong[:8]
            ]
    return gate, failures


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def card(gate: dict, failures: list[dict]) -> str:
    m = json.loads((DERIVED / "metrics.json").read_text(encoding="utf-8"))
    audit = json.loads((DERIVED / "audit.json").read_text(encoding="utf-8"))
    rows = []
    for head in HEADS:
        e = m["heads"][head]
        kw = e.get("keyword")
        rows.append(
            f"| {head} | {e['classes']} | {pct(e['model']['accuracy'])} ({pct(e['model']['accuracy_ci'][0])} to {pct(e['model']['accuracy_ci'][1])}) "
            f"| {e['model']['macro_f1']:.3f} | {pct(e['majority']['accuracy'])} | {pct(kw['accuracy']) if kw else 'n/a'} | {e['model']['n']} |"
        )
    gates = []
    for head in HEADS:
        g = gate["heads"][head]
        if g["useful"]:
            gates.append(
                f"| {head} | {g['threshold']} | {pct(g['val_coverage'])} / {pct(g['val_accuracy'])} | {pct(g['test_coverage'])} / {pct(g['test_accuracy'])} | yes |"
            )
        else:
            gates.append(
                f"| {head} | none reaches {pct(gate['target_accuracy'])} | best coverage {pct(g['best_val_coverage_at_any_threshold'])} | n/a | **not useful as a gate** |"
            )
    fails = "\n".join(
        f"| {f['query'][:90]} | `{f['predicted']}` | {f['confidence']} | `{f['teacher']}` |" for f in failures
    )
    st = audit["topic_status"]
    return f"""# Router model card (router-v1)

> Generated by `uv run python eval/models/calibrate.py` (do not edit by hand; a test fails if it is stale). Artifact sha256 `{gate["artifact_sha256"]}`.

## What it is

A multi-head text classifier for the Route stage (D-20). Features: word 1 to 2 gram and character 3 to 5 gram TF-IDF. One logistic regression
per head: **topic** (the 53 syllabus topics plus `none`), **domain**, **pattern** (v3's artifact type) and **complexity**. Weights below
0.1 are dropped and the rest rounded to 4 places, and every number below is for that shipped, pruned model. Inference is pure Python from a JSON
file (no numpy, no network). A router uses a head's answer only above its confidence threshold and sends everything else to the LLM.

## Data and its limits

- Questions and labels come from Synapse v3 (`Azimlearning/GenUI-Education`, `Synapse-V3/ml/router-distill/dataset/clean`, commit `{SOURCE_COMMIT}`).
  They were **written and labelled by an LLM teacher**, not by students or teachers. Held-out accuracy is **agreement with that teacher**, not
  correctness about the world. The v3 notes put the teacher's own agreement with itself at about 75 percent on some styles, which caps what any
  student can show on `pattern` and `complexity`.
- {audit["rows_out"]["train"]} training, {audit["rows_out"]["val"]} validation, {audit["rows_out"]["test"]} test questions after removing {audit["exact_duplicates_removed_from_train"]} exact duplicates and
  {audit["train_rows_removed_for_test_leakage"]["exact"] + audit["train_rows_removed_for_test_leakage"]["near"]} training questions that duplicated or nearly duplicated a test question.
- **Stale topic tags.** {st["train"].get("stale", 0)} training and {st["test"].get("stale", 0)} test rows carry a topic tag from an older taxonomy. Their topic is
  unknown, so they are excluded from the topic head only (they still train and test the other heads). Topic accuracy is on {m["heads"]["topic"]["model"]["n"]} test questions.
- `none` means "no syllabus topic tagged in the source" ({st["train"].get("untagged", 0)} training rows). It is a weak class: some of those questions are in
  fact on-syllabus.
- Domain classes `earth_space` and `math_adjacent` are small ({audit["class_counts"]["domain"]["train"].get("earth_space", 0)} and {audit["class_counts"]["domain"]["train"].get("math_adjacent", 0)} training rows).

## Results on the held-out test (95 percent bootstrap interval on accuracy)

| Head | Classes | Model accuracy | Macro-F1 | Majority baseline | Keyword baseline | n |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

The keyword baseline scores each topic by overlap of the question with the topic's label and hint words; it exists to show whether the model
earns its keep over a rule anyone could write. The complexity head beats its majority baseline by a small margin; treat it as weak.

## Confidence gate

The threshold for each head is the lowest confidence at which the questions the model answers by itself reach {pct(gate["target_accuracy"])} accuracy on the
validation set, with at least {pct(gate["min_coverage"])} coverage. Test numbers are then measured once, with that threshold fixed.

| Head | Threshold | Validation coverage / accuracy | Test coverage / accuracy | Useful as a gate |
|---|---|---|---|---|
{chr(10).join(gates)}

The router never trusts a local `none` for the topic head and asks the fallback instead (on the 24-question golden set for the first vertical, 7 of 24 topics were wrongly `none`; a keyword second opinion was tried and was no better than chance). Coverage is the share of questions the model answers without the LLM. A head that is "not useful as a gate" is not used by the router.

## Most confident topic errors on the test set

| Question | Model said | Confidence | Teacher said |
|---|---|---|---|
{fails}

Several of these are the teacher's choice among overlapping topics rather than a clear model mistake; none is a verdict on the question's science.

## Do not use it for

- Deciding whether an Environment is correct (it knows nothing about physics).
- Anything unattended below a head's threshold, or on a head marked not useful.
- Questions in Bahasa Malaysia or heavy slang: the training data is English.
- Measuring students: it predicts what an LLM teacher would label.

## Retrain

`uv run python eval/models/data.py build` (needs the v3 clone, set `ROUTER_DATA_DIR`), then `uv run python eval/models/train_router.py`, then
`uv run python eval/models/calibrate.py`. Training takes about two minutes on CPU and is deterministic. A bigger dataset arrives with the full KSSM
ingestion (deferred to local); retrain then and re-read this card.
"""


def main() -> int:
    gate, failures = build()
    gate_text = json.dumps(gate, indent=2, sort_keys=True) + "\n"
    card_text = card(gate, failures)
    if "--check" in sys.argv:
        stale = [
            p.name
            for p, t in ((GATE, gate_text), (CARD, card_text))
            if not p.exists() or p.read_text(encoding="utf-8") != t
        ]
        if stale:
            print("stale:", ", ".join(stale))
            return 1
        print("up to date")
        return 0
    GATE.write_text(gate_text, encoding="utf-8")
    CARD.write_text(card_text, encoding="utf-8")
    for head, g in gate["heads"].items():
        print(head, g)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
