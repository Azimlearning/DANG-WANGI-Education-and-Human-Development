"""Run the golden set for the first vertical: how well does the local router find the topic, and does the whole pipeline on fakes produce a verified
Environment for each question? Free (fakes). The set is pinned by hash (hard constraint 9).

    uv run python eval/golden/run.py            # router only, instant
    uv run python eval/golden/run.py --pipeline # the full pipeline per question in real Chromium (about 15 seconds each)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.core.settings import Settings  # noqa: E402
from api.llm.factory import build_ledger, build_llm_service  # noqa: E402
from api.pipeline import run as pipeline  # noqa: E402
from api.routing.router import route  # noqa: E402
from api.verify.store import SqliteEnvironmentStore  # noqa: E402

SET = REPO / "eval" / "golden" / "vertical.json"
PIN = REPO / "eval" / "golden" / "vertical.sha256"


def load() -> list[dict]:
    text = SET.read_text(encoding="utf-8")
    if hashlib.sha256(text.encode()).hexdigest() != PIN.read_text(encoding="utf-8").strip():
        raise SystemExit(
            "the golden set changed without a declared amendment: update eval/golden/vertical.sha256 and the changelog"
        )
    return json.loads(text)["questions"]


async def route_all(questions: list[dict]) -> list[dict]:
    out = []
    for q in questions:
        r = await route(q["question"], llm=None)  # no fallback: measures what the local model alone does
        out.append(
            {
                "id": q["id"],
                "expect": q["expect_topic"],
                "got": r.topic.value,
                "source": r.topic.source,
                "conf": r.topic.confidence,
            }
        )
    return out


async def pipeline_all(questions: list[dict]) -> list[dict]:
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(_env_file=None, data_dir=Path(tmp), kit_dist_dir=REPO / "packages" / "kit" / "dist")  # type: ignore[call-arg]
        llm = build_llm_service(settings, build_ledger(settings))
        deps = pipeline.Deps(
            kit_dist=settings.kit_dist_dir,
            public_origin=settings.public_origin,
            store=SqliteEnvironmentStore(Path(tmp) / "envs.db"),
            llm=llm,
            interaction_seconds=2.0,
        )
        for q in questions:
            events = [e async for e in pipeline.run(q["question"], deps)]
            env = next((e.block for e in events if e.type == "environment"), None)
            degraded = [e.note for e in events if e.type == "stage" and e.status == "degraded"]
            out.append(
                {
                    "id": q["id"],
                    "environment": env.title if env else None,
                    "lane": env.lane if env else None,
                    "degraded": degraded,
                }
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", action="store_true")
    args = ap.parse_args()
    questions = load()
    routed = asyncio.run(route_all(questions))
    right = sum(r["expect"] == r["got"] for r in routed)
    local = sum(r["source"] == "local" for r in routed)
    print(
        f"router topic: {right} of {len(routed)} correct; {local} answered locally (the rest would go to the LLM fallback)"
    )
    for r in routed:
        if r["expect"] != r["got"]:
            print(f"  miss {r['id']}: expected {r['expect']}, got {r['got']} ({r['source']}, {r['conf']})")
    if args.pipeline:
        results = asyncio.run(pipeline_all(questions))
        made = [r for r in results if r["environment"]]
        print(f"pipeline on fakes: {len(made)} of {len(results)} questions got a verified Environment")
        for r in results:
            if not r["environment"]:
                print(f"  no environment {r['id']}: {r['degraded']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
