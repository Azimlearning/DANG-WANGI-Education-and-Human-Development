"""Print a fixed random sample of the router's held-out questions beside its predictions and the teacher's labels, for a person to judge.

    uv run python eval/models/spot_check.py [count]        # free, no model call; same 50 every time (seed 20261018)

The model card measures AGREEMENT WITH AN LLM TEACHER, not truth. This prints the evidence for the other number: a person reads each question and
says whether the router's label is right. The judgments of the first pass (2026-10-18) are in refdocs/evidence/2026-10-18-p1b-router-spot-check.md.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from api.models import router_model  # noqa: E402

SEED = 20261018


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    model = router_model.load()
    rows = [json.loads(line) for line in (REPO / "data/models/router/test.jsonl").read_text(encoding="utf-8").splitlines()]
    random.Random(SEED).shuffle(rows)
    for number, row in enumerate(rows[:count], start=1):
        got = model.predict(row["query"])

        def show(head: str, got=got) -> str:
            return f"{got[head].label}({got[head].confidence:.2f})"

        print(f"{number:02d} Q: {row['query'][:150]}")
        print(f"    ROUTER  domain={show('domain')} pattern={show('pattern')} complexity={show('complexity')} topic={show('topic')}")
        print(f"    TEACHER domain={row['domain']} pattern={row['pattern']} complexity={row['complexity']} topic={row['topic']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
