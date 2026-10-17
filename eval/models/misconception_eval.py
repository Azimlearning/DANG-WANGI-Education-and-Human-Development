"""Measure the misconception matcher on the labelled probe set (free, no model call).

    uv run python eval/models/misconception_eval.py

Reports, at the matcher's shipped threshold and across a sweep of thresholds: how often the top match is the right misconception for a student who
states one (recall), and how often it fires on a neutral or off-topic question (false positives). The probe set is `misconception_probe.json`; it was
written by the same assistant family as the matcher, so it measures the matcher against a plausible reading, not against students.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from api.models.misconceptions import default_matcher  # noqa: E402

PROBE = Path(__file__).with_name("misconception_probe.json")


def load_items() -> list[dict]:
    return json.loads(PROBE.read_text(encoding="utf-8"))["items"]


def evaluate(min_score: float) -> dict:
    matcher = default_matcher()
    positives = hits = wrong = false_positive = quiet = 0
    for item in load_items():
        top = matcher.match(item["q"], top=1, min_score=min_score)
        if item["kind"] == "positive":
            positives += 1
            if top and top[0].id == item["id"]:
                hits += 1
            elif top:
                wrong += 1
        else:
            quiet += 1
            false_positive += 1 if top else 0
    return {
        "min_score": min_score,
        "recall": hits / positives,
        "wrong_id": wrong,
        "missed": positives - hits - wrong,
        "false_positive_rate": false_positive / quiet,
        "false_positives": false_positive,
        "quiet_items": quiet,
        "positives": positives,
    }


def main() -> int:
    shipped = evaluate(1.0)
    print(
        f"shipped threshold {shipped['min_score']}: right id first on {int(shipped['recall'] * shipped['positives'])} of {shipped['positives']} "
        f"student statements ({shipped['recall']:.0%}), wrong id on {shipped['wrong_id']}, missed {shipped['missed']}; "
        f"fires on {shipped['false_positives']} of {shipped['quiet_items']} neutral or off-topic questions ({shipped['false_positive_rate']:.0%})"
    )
    print("\nthreshold sweep")
    for threshold in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0):
        r = evaluate(threshold)
        print(f"  min_score {threshold:>4}: recall {r['recall']:.0%}  false positives {r['false_positive_rate']:.0%}")
    print("\nper-item (positives that failed, and every false positive)")
    matcher = default_matcher()
    for item in load_items():
        top = matcher.match(item["q"], top=1)
        got = top[0].id if top else None
        if (item["kind"] == "positive" and got != item["id"]) or (item["kind"] != "positive" and got):
            print(f"  [{item['kind']}] {item['q']!r}\n      expected {item['id']}, got {got} ({top[0].score if top else 0})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
