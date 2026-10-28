"""The W13 GPU job: does a trained multilingual encoder route Malay questions better than the glossary guard? (D-63) Run it on a free Colab or Kaggle GPU, never in the API.

    colab run --gpu T4 eval/models/colab/gpu_job.py --data DATA_DIR --out OUT_DIR      # Linux or macOS, or WSL; see README.md for Kaggle and the Colab web page

DATA_DIR holds `train.jsonl`, `val.jsonl`, `test.jsonl` (the router's English questions, `data/models/router/`) and `bm_probe.jsonl` (the Malay probe). The job:

1. translates the English questions into Bahasa Melayu with NLLB-200 (`facebook/nllb-200-distilled-600M`, language `zsm_Latn`), writing `train_ms.jsonl`, `val_ms.jsonl` and
   `test_ms.jsonl` with the same labels. Machine translation, so noisy: it is training and measuring data, not a reference.
2. fine-tunes `intfloat/multilingual-e5-small` with a linear topic head on the English train questions plus their Malay translations, and scores it on the English test, the
   translated test and the hand-written probe, at the library's gate (0.55, a local "none" never trusted), exactly as `eval/models/bm_probe.py` scores the router.
3. writes `report.json`. The encoder is a measurement, not something the API loads: the API stays pure Python with no heavy dependency (D-20). If the encoder beats the glossary
   guard by a clear margin, the translated files are what retrains the shippable TF-IDF router (`eval/models/train_router.py --extra-train`), and the encoder is only the evidence
   that dense models help (A-9, D-12: dense only if measured to help).

Nothing here is paid: the models are open and the GPU is the free tier. Nothing leaves the machine except the model downloads. Read the current `transformers` documentation before
changing the model calls (CLAUDE.md rule 6); the calls below follow its AutoModel, AutoTokenizer and generate interfaces.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

GATE = 0.55
"""The library's confidence gate (`api/pipeline/library.INSTANTIATE_MIN_CONFIDENCE`). Copied, not imported: this file runs on a machine that has only this file and the data."""
NLLB = "facebook/nllb-200-distilled-600M"
ENCODER = "intfloat/multilingual-e5-small"
SEED = 20261027


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def topic_rows(rows: list[dict]) -> list[dict]:
    """The rows that have a topic. A row whose topic tag is from an older taxonomy has `topic: null` and trains the other heads only."""
    return [r for r in rows if r.get("topic")]


def label_space(*sets: list[dict]) -> list[str]:
    """A fixed, sorted list of every topic seen, with `none` always present: the same space on every run."""
    return sorted({r["topic"] for rows in sets for r in rows if r.get("topic")} | {"none"})


def gate_metrics(predicted: list[str], confidence: list[float], wanted: list[str], threshold: float = GATE) -> dict:
    """What `eval/models/bm_probe.py` reports: topic accuracy, the share answered from the library, and how often that answer is right. A `none` is never trusted."""
    if not (len(predicted) == len(confidence) == len(wanted)) or not wanted:
        raise ValueError("predicted, confidence and wanted must be the same non-zero length")
    right = sum(p == w for p, w in zip(predicted, wanted, strict=True))
    served = [(p, w) for p, c, w in zip(predicted, confidence, wanted, strict=True) if p != "none" and c >= threshold]
    return {
        "n": len(wanted),
        "topic_accuracy": round(right / len(wanted), 3),
        "answered_from_library": round(len(served) / len(wanted), 3),
        "right_when_answered": round(sum(p == w for p, w in served) / len(served), 3) if served else None,
    }


def translate(texts: list[str], batch: int = 32) -> list[str]:
    import torch  # pyright: ignore[reportMissingImports]  # installed on the GPU box, not here
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # pyright: ignore[reportMissingImports]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(NLLB, src_lang="eng_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(NLLB).to(device).eval()
    if device == "cuda":
        model = model.half()
    bos = tokenizer.convert_tokens_to_ids("zsm_Latn")
    out: list[str] = []
    for i in range(0, len(texts), batch):
        encoded = tokenizer(texts[i : i + batch], return_tensors="pt", padding=True, truncation=True, max_length=96).to(device)
        with torch.no_grad():
            generated = model.generate(**encoded, forced_bos_token_id=bos, max_new_tokens=96, num_beams=4)
        out.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
        print(f"translated {len(out)} of {len(texts)}", flush=True)
    return out


def translate_split(rows: list[dict]) -> list[dict]:
    done = translate([r["query"] for r in rows])
    return [{**r, "query": t, "translated_from": r["query"]} for r, t in zip(rows, done, strict=True)]


def fine_tune_and_score(train: list[dict], val: list[dict], evaluations: dict[str, list[dict]], labels: list[str], epochs: int = 4) -> dict:
    import torch  # pyright: ignore[reportMissingImports]  # installed on the GPU box, not here
    from torch import nn  # pyright: ignore[reportMissingImports]
    from transformers import AutoModel, AutoTokenizer  # pyright: ignore[reportMissingImports]

    random.seed(SEED)
    torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    index = {t: i for i, t in enumerate(labels)}
    tokenizer = AutoTokenizer.from_pretrained(ENCODER)

    class TopicEncoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = AutoModel.from_pretrained(ENCODER)
            self.head = nn.Linear(self.encoder.config.hidden_size, len(labels))

        def forward(self, texts: list[str]) -> torch.Tensor:
            encoded = tokenizer(["query: " + t for t in texts], return_tensors="pt", padding=True, truncation=True, max_length=64).to(device)
            hidden = self.encoder(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)  # mean pooling, as the E5 models are trained
            return self.head(torch.nn.functional.normalize(pooled, dim=-1) * 20.0)

    model = TopicEncoder().to(device)
    optimiser = torch.optim.AdamW([{"params": model.encoder.parameters(), "lr": 3e-5}, {"params": model.head.parameters(), "lr": 2e-3}], weight_decay=0.01)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)

    def predict(rows: list[dict]) -> tuple[list[str], list[float]]:
        model.eval()
        names: list[str] = []
        conf: list[float] = []
        with torch.no_grad():
            for i in range(0, len(rows), 64):
                probs = torch.softmax(model([r["query"] for r in rows[i : i + 64]]), dim=-1)
                top = probs.max(dim=-1)
                names.extend(labels[k] for k in top.indices.tolist())
                conf.extend(round(v, 4) for v in top.values.tolist())
        return names, conf

    best = {"val": -1.0, "state": None}
    for epoch in range(epochs):
        model.train()
        order = random.sample(range(len(train)), len(train))
        for i in range(0, len(order), 32):
            chunk = [train[j] for j in order[i : i + 32]]
            loss = loss_fn(model([r["query"] for r in chunk]), torch.tensor([index[r["topic"]] for r in chunk], device=device))
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
        names, _ = predict(val)
        accuracy = sum(n == r["topic"] for n, r in zip(names, val, strict=True)) / len(val)
        print(f"epoch {epoch + 1}: validation topic accuracy {accuracy:.3f}", flush=True)
        if accuracy > best["val"]:
            best = {"val": accuracy, "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}}
    model.load_state_dict(best["state"])
    report: dict = {"validation_accuracy": round(best["val"], 3)}
    for name, rows in evaluations.items():
        names, conf = predict(rows)
        report[name] = gate_metrics(names, conf, [r["topic"] for r in rows])
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-translate", action="store_true", help="reuse train_ms.jsonl, val_ms.jsonl and test_ms.jsonl already in --out")
    ap.add_argument("--epochs", type=int, default=4)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    train, val, test = (topic_rows(read_jsonl(args.data / f"{n}.jsonl")) for n in ("train", "val", "test"))
    probe = read_jsonl(args.data / "bm_probe.jsonl")
    if args.skip_translate:
        train_ms, val_ms, test_ms = (read_jsonl(args.out / f"{n}_ms.jsonl") for n in ("train", "val", "test"))
    else:
        train_ms, val_ms, test_ms = (translate_split(rows) for rows in (train, val, test))
        for name, rows in (("train", train_ms), ("val", val_ms), ("test", test_ms)):
            write_jsonl(args.out / f"{name}_ms.jsonl", rows)
    labels = label_space(train, val, test, probe)
    report = fine_tune_and_score(
        train + train_ms,
        val + val_ms,
        {"english_test": test, "malay_test_translated": test_ms, "malay_probe": probe},
        labels,
        args.epochs,
    )
    report.update(encoder=ENCODER, translator=NLLB, gate=GATE, seed=SEED, train_rows=len(train) + len(train_ms))
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
