"""How well does the topic router cope with questions in Bahasa Melayu? (W13, D-63) Free: CPU only, no model call.

    uv run python -m eval.models.bm_probe                 # the shipped artifact, on the probe set
    uv run python -m eval.models.bm_probe --artifact PATH # another artifact (a retrained or augmented one)

The probe set (`data/models/router/bm_probe.jsonl`) is 68 questions written by the build assistant, not by students or teachers: 53 in Bahasa Melayu and 15 mixing Malay with
English the way students write. Each carries the topic of a Plan the library covers. It is small and unreviewed, so read the numbers as a smoke gauge for "does the English-only
model understand Malay at all", not as accuracy. The topic is judged at the library's own gate (`library.INSTANTIATE_MIN_CONFIDENCE`), because that decides whether a Malay
question is answered from the library or sent on to the model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.models import router_model  # noqa: E402
from api.pipeline.library import INSTANTIATE_MIN_CONFIDENCE  # noqa: E402
from api.routing.router import prepare  # noqa: E402

PROBE = REPO / "data" / "models" / "router" / "bm_probe.jsonl"


def load_probe() -> list[dict]:
    return [json.loads(line) for line in PROBE.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(model: router_model.RouterModel, rows: list[dict], guarded: bool = True) -> dict:
    """`guarded` runs the question through the same Malay guard the router uses (`routing.router.prepare`); unguarded shows the English-only model as it was."""
    out: dict[str, dict] = {}
    for style in ("ms", "mixed", "all"):
        subset = [r for r in rows if style == "all" or r["style"] == style]
        right = served = served_right = 0
        for r in subset:
            prepared = prepare(r["query"], model) if guarded else None
            if prepared is not None and not prepared.trusted:
                continue  # sent to the fallback: neither right nor served from the library
            top = model.predict(prepared.query if prepared is not None else r["query"])["topic"]
            right += top.label == r["topic"]
            # The router never trusts a local "none" (`routing.router.route`): it goes to the fallback, so it is neither served from the library nor a wrong topic.
            if top.label != "none" and top.confidence >= INSTANTIATE_MIN_CONFIDENCE:
                served += 1
                served_right += top.label == r["topic"]
        out[style] = {
            "n": len(subset),
            "topic_accuracy": round(right / len(subset), 3),
            "answered_from_library": round(served / len(subset), 3),
            "right_when_answered": round(served_right / served, 3) if served else None,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", type=Path, default=router_model.DEFAULT_ARTIFACT)
    ap.add_argument("--unguarded", action="store_true", help="the model as it was, with no Malay guard")
    args = ap.parse_args(argv)
    model = router_model.load(args.artifact)
    result = score(model, load_probe(), guarded=not args.unguarded)
    print(json.dumps({"artifact": args.artifact.name, "sha256": model.sha256[:12], "gate": INSTANTIATE_MIN_CONFIDENCE, "guarded": not args.unguarded, "scores": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
