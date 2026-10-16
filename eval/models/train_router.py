"""Train the multi-head router (TF-IDF + logistic regression), compare it with the baselines, and export a JSON artifact.

    uv run python eval/models/train_router.py          # trains, prints the comparison table, writes the artifact and metrics

Provenance: new in v4 (v3's router was a Keras student; D-20 chose a classical model that exports to plain JSON). Training is free (CPU,
seconds) and deterministic: fixed seeds, lbfgs, sorted outputs, so two runs give byte-identical artifacts.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from eval.models.baselines import KeywordRouter, Majority  # noqa: E402
from eval.models.data import DERIVED, HEADS, SEED, SOURCE_COMMIT, load_split  # noqa: E402

ARTIFACT = REPO / "api" / "models" / "artifacts" / "router-v1.json"
METRICS = DERIVED / "metrics.json"
C_GRID = (1.0, 3.0, 10.0, 30.0, 100.0)
FEATURES = (
    {"name": "word", "kind": "word", "ngram_range": [1, 2], "min_df": 2},
    {"name": "char", "kind": "char_wb", "ngram_range": [3, 5], "min_df": 5},
)
DECIMALS = 4
PRUNE_BELOW = 0.1  # weights smaller than this are dropped; measured to cost under 0.5 points on every head
BOOTSTRAPS = 1000


def make_vectorizers() -> list[TfidfVectorizer]:
    return [
        TfidfVectorizer(
            analyzer=f["kind"],
            ngram_range=tuple(f["ngram_range"]),
            min_df=f["min_df"],
            sublinear_tf=True,
            lowercase=True,
            dtype=np.float64,
        )
        for f in FEATURES
    ]


def stack(vectorizers: list[TfidfVectorizer], queries: list[str], fit: bool):
    from scipy.sparse import hstack

    mats = [(v.fit_transform(queries) if fit else v.transform(queries)) for v in vectorizers]
    return hstack(mats).tocsr()


def head_rows(rows: list[dict], head: str) -> tuple[list[str], list]:
    """Queries and labels for a head. The topic head skips rows whose v3 tag is unknown to the current taxonomy."""
    keep = [r for r in rows if r[head] is not None]
    return [r["query"] for r in keep], [r[head] for r in keep]


def bootstrap_ci(y_true: list, y_pred: list, metric, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(y_true)
    scores = []
    for _ in range(BOOTSTRAPS):
        idx = [rng.randrange(n) for _ in range(n)]
        scores.append(metric([y_true[i] for i in idx], [y_pred[i] for i in idx]))
    scores.sort()
    return scores[int(0.025 * BOOTSTRAPS)], scores[int(0.975 * BOOTSTRAPS) - 1]


def macro_f1(y_true: list, y_pred: list) -> float:
    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def score(y_true: list, y_pred: list, seed: int) -> dict:
    acc = float(accuracy_score(y_true, y_pred))
    f1 = macro_f1(y_true, y_pred)
    return {
        "n": len(y_true),
        "accuracy": round(acc, 4),
        "accuracy_ci": [
            round(x, 4) for x in bootstrap_ci(y_true, y_pred, lambda a, b: float(accuracy_score(a, b)), seed)
        ],
        "macro_f1": round(f1, 4),
        "macro_f1_ci": [round(x, 4) for x in bootstrap_ci(y_true, y_pred, macro_f1, seed + 1)],
    }


def fit_all() -> dict:
    train, val, test = load_split("train"), load_split("val"), load_split("test")
    models: dict = {}
    vectorizers = make_vectorizers()
    x_train = stack(vectorizers, [r["query"] for r in train], fit=True)  # features fitted on train only
    for v in vectorizers:
        v.idf_ = np.round(v.idf_, 6)  # the shipped idf is rounded; evaluate exactly what ships
    x_train = stack(vectorizers, [r["query"] for r in train], fit=False)
    x_val = stack(vectorizers, [r["query"] for r in val], fit=False)
    x_test = stack(vectorizers, [r["query"] for r in test], fit=False)
    results: dict = {
        "heads": {},
        "source_commit": SOURCE_COMMIT,
        "seed": SEED,
        "features": len(vectorizers[0].vocabulary_) + len(vectorizers[1].vocabulary_),
    }
    maj_domain = None
    for head in HEADS:
        tr_idx = [i for i, r in enumerate(train) if r[head] is not None]
        va_idx = [i for i, r in enumerate(val) if r[head] is not None]
        te_idx = [i for i, r in enumerate(test) if r[head] is not None]
        y_tr = [train[i][head] for i in tr_idx]
        y_va = [val[i][head] for i in va_idx]
        y_te = [test[i][head] for i in te_idx]
        best = None
        for c in C_GRID:
            clf = LogisticRegression(C=c, class_weight="balanced", max_iter=3000, random_state=SEED)
            clf.fit(x_train[tr_idx], y_tr)
            acc = float(accuracy_score(y_va, clf.predict(x_val[va_idx])))
            if best is None or acc > best[0] + 1e-12:
                best = (acc, c, clf)
        assert best is not None
        val_acc, c, clf = best
        clf.coef_ = np.where(
            np.abs(clf.coef_) < PRUNE_BELOW, 0.0, np.round(clf.coef_, DECIMALS)
        )  # evaluate exactly what ships
        clf.intercept_ = np.round(clf.intercept_, DECIMALS)
        val_acc = float(accuracy_score(y_va, clf.predict(x_val[va_idx])))
        pred = list(clf.predict(x_test[te_idx]))
        queries_te = [test[i]["query"] for i in te_idx]
        majority = Majority(y_tr)
        base_majority = [majority.predict(q) for q in queries_te]
        entry = {
            "chosen_C": c,
            "val_accuracy": round(val_acc, 4),
            "model": score(y_te, pred, SEED),
            "majority": score(y_te, base_majority, SEED),
            "majority_label": majority.label,
            "classes": len(clf.classes_),
        }
        if head == "domain":
            maj_domain = majority.label
        results["heads"][head] = entry
        models[head] = clf
    kw = KeywordRouter(majority_domain=maj_domain or "biology")
    for head, fn in (("topic", kw.topic), ("domain", kw.domain)):
        te_idx = [i for i, r in enumerate(test) if r[head] is not None]
        results["heads"][head]["keyword"] = score(
            [test[i][head] for i in te_idx], [fn(test[i]["query"]) for i in te_idx], SEED
        )
    return {
        "vectorizers": vectorizers,
        "models": models,
        "results": results,
        "x_val": x_val,
        "x_test": x_test,
        "val": val,
        "test": test,
    }


def export(trained: dict) -> dict:
    vecs = trained["vectorizers"]
    offsets, features = 0, []
    for spec, v in zip(FEATURES, vecs, strict=True):
        vocab = sorted(v.vocabulary_.items(), key=lambda kv: kv[1])
        features.append(
            {
                "name": spec["name"],
                "kind": spec["kind"],
                "ngram_range": spec["ngram_range"],
                "offset": offsets,
                "terms": [t for t, _ in vocab],
                "idf": [round(float(x), 6) for x in v.idf_],
            }
        )
        offsets += len(vocab)
    heads = {}
    for head, clf in trained["models"].items():
        classes = [str(c) if not isinstance(c, (int, np.integer)) else int(c) for c in clf.classes_]
        coef = clf.coef_
        if len(classes) == 2:  # binary: scikit-learn stores one row; expand to two
            coef = np.vstack([-coef[0], coef[0]])
            intercept = [-float(clf.intercept_[0]), float(clf.intercept_[0])]
        else:
            intercept = [float(x) for x in clf.intercept_]
        rows = []
        for k in range(len(classes)):
            nz = np.nonzero(np.abs(coef[k]) >= PRUNE_BELOW)[0]
            rows.append([[int(i), round(float(coef[k][i]), DECIMALS)] for i in nz])
        heads[head] = {"classes": classes, "intercept": [round(x, DECIMALS) for x in intercept], "weights": rows}
    body = {
        "format": 1,
        "name": "router-v1",
        "source_commit": SOURCE_COMMIT,
        "seed": SEED,
        "features": features,
        "heads": heads,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["content_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return body


def parity_record(trained: dict, artifact: dict) -> dict:
    """What scikit-learn says about every test question with the SHIPPED (pruned, rounded) model. The pure-Python inference must match."""
    rows = [{"query": r["query"]} for r in trained["test"]]
    for head, clf in trained["models"].items():
        proba = clf.predict_proba(trained["x_test"])
        for i, p in enumerate(proba):
            k = int(np.argmax(p))
            rows[i][head] = [
                str(clf.classes_[k]) if not isinstance(clf.classes_[k], (int, np.integer)) else int(clf.classes_[k]),
                round(float(p[k]), 6),
            ]
    return {"artifact_sha256": artifact["content_sha256"], "rows": rows}


def main() -> int:
    trained = fit_all()
    artifact = export(trained)
    (DERIVED / "parity.json").write_text(
        json.dumps(parity_record(trained, artifact), sort_keys=True) + "\n", encoding="utf-8"
    )
    text = json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(text, encoding="utf-8")
    METRICS.write_text(json.dumps(trained["results"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"artifact {ARTIFACT.relative_to(REPO)}: {len(text) / 1e6:.2f} MB, sha {artifact['content_sha256'][:12]}")
    print(f"{'head':11} {'model acc':>10} {'macroF1':>8} {'majority':>9} {'keyword':>8}   verdict")
    for head, e in trained["results"]["heads"].items():
        kw = e.get("keyword", {}).get("accuracy")
        beats = e["model"]["accuracy"] > e["majority"]["accuracy"] and (kw is None or e["model"]["accuracy"] > kw)
        print(
            f"{head:11} {e['model']['accuracy']:>10} {e['model']['macro_f1']:>8} {e['majority']['accuracy']:>9} {kw if kw is not None else '-':>8}   {'beats baselines' if beats else 'DOES NOT BEAT BASELINES'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
