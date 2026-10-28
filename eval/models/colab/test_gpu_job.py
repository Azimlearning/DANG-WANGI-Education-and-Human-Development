"""The parts of the W13 GPU job that need no GPU and no download (D-63): data handling and the gate metrics. The model calls themselves run only on the GPU box."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.models.colab import gpu_job as job


def test_the_job_imports_without_a_gpu_library() -> None:
    assert not hasattr(job, "torch") and not hasattr(job, "transformers")  # the heavy imports are inside the functions, so this runs on a laptop
    assert job.GATE == 0.55 and job.NLLB.startswith("facebook/nllb") and "e5" in job.ENCODER


def test_the_gate_here_is_the_gate_the_library_uses() -> None:
    from api.pipeline.library import INSTANTIATE_MIN_CONFIDENCE

    assert job.GATE == INSTANTIATE_MIN_CONFIDENCE


def test_the_label_space_is_sorted_and_always_has_none() -> None:
    rows = [{"topic": "b"}, {"topic": "a"}, {"topic": None}]
    assert job.label_space(rows, [{"topic": "c"}]) == ["a", "b", "c", "none"]
    assert job.topic_rows(rows) == [{"topic": "b"}, {"topic": "a"}]


def test_gate_metrics_never_trust_a_none_and_count_what_is_served() -> None:
    out = job.gate_metrics(["a", "a", "none", "b"], [0.9, 0.3, 0.99, 0.6], ["a", "a", "a", "c"])
    assert out == {"n": 4, "topic_accuracy": 0.5, "answered_from_library": 0.5, "right_when_answered": 0.5}
    assert job.gate_metrics(["a"], [0.1], ["a"])["right_when_answered"] is None
    with pytest.raises(ValueError, match="same non-zero length"):
        job.gate_metrics(["a"], [], ["a"])


def test_the_scores_agree_with_the_probe_scorer_on_the_same_predictions() -> None:
    """The job's metrics and `eval/models/bm_probe.py` must mean the same thing, or the encoder is compared with the guard on different rulers."""
    from api.models import router_model
    from api.routing.router import prepare
    from eval.models.bm_probe import load_probe, score

    model = router_model.default_model()
    rows = load_probe()
    names, conf = [], []
    for r in rows:
        prepared = prepare(r["query"], model)
        if not prepared.trusted:
            names.append("none")
            conf.append(0.0)
            continue
        top = model.predict(prepared.query)["topic"]
        names.append(str(top.label))
        conf.append(top.confidence)
    ours = job.gate_metrics(names, conf, [r["topic"] for r in rows])
    theirs = score(model, rows)["all"]
    assert ours["answered_from_library"] == theirs["answered_from_library"]
    assert ours["right_when_answered"] == theirs["right_when_answered"]


def test_jsonl_round_trips_with_non_ascii_text(tmp_path: Path) -> None:
    rows = [{"query": "Mengapa spring memanjang?", "topic": "x", "note": "°C"}]
    job.write_jsonl(tmp_path / "a.jsonl", rows)
    assert job.read_jsonl(tmp_path / "a.jsonl") == rows
