"""Flag-to-regression records (P5): when enough people flag an Environment it is taken out of the library, and one line is written that says what was flagged and
why, so a person can turn it into a planted-defect row for the verifier (eval/l6) or a fixed Plan. One JSON line per eviction in `<data_dir>/regressions.jsonl`.

The record keeps the Environment's id, title, hashes and the flag notes (each cut to 240 characters, at most five). It never keeps a question. There is no automatic
consumer yet: the list is read by a person (`uv run python -m api.regressions`), which is the honest state of "writes a regression eval".
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)


def record(
    path: Path | None,
    *,
    env_id: str,
    title: str,
    lane: str,
    label: str,
    kit_version: str,
    html_sha256: str,
    plan_summary: str,
    flags: int,
    notes: list[str],
) -> None:
    """Append one record. No-op when `path` is None; a failure to write is logged and never breaks the request."""
    if path is None:
        return
    row = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "env_id": env_id,
        "title": title[:120],
        "lane": lane,
        "label": label,
        "kit_version": kit_version,
        "html_sha256": html_sha256,
        "plan_summary": plan_summary[:240],
        "flags": flags,
        "notes": [n[:240] for n in notes[:5]],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        log.exception("could not write the regression record for %s", env_id)


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("data") / "regressions.jsonl"
    rows = load(path)
    if not rows:
        print(f"no flagged Environments in {path}")
        return 0
    for r in rows:
        print(f"{r['at']}  {r['env_id']}  {r['title']}  ({r['label']}, {r['flags']} flags)")
        for n in r["notes"]:
            print(f"    - {n}")
    print(f"{len(rows)} flagged Environment(s). Turn each into an eval/l6 row or a fixed Plan, then delete its line.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
