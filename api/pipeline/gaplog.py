"""The Kit gap log: every Free-lane generation is a question the Kit could not express, and so a candidate for a new component (hard constraint 3,
PRD principle 8). One JSON line per event.

It records the hash of the question, never the question (traces do the same: no student text is kept server-side), the routed topic, domain and
pattern, and the reason: `assembly_gap:<part>` or the plan check codes. That is what a Kit backlog needs. A logging failure never breaks an answer.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)


def record(
    path: Path | None,
    *,
    question_sha256: str,
    topic: str,
    domain: str,
    pattern: str,
    reason: str,
    outcome: str,
    env_id: str | None = None,
) -> None:
    """Append one gap record. `outcome` is what the student got: the Free Environment's lane or the written answer. No-op when `path` is None."""
    if path is None:
        return
    row = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "question_sha256": question_sha256,
        "topic": topic,
        "domain": domain,
        "pattern": pattern,
        "reason": reason[:200],
        "outcome": outcome,
        "env_id": env_id,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        log.warning("could not write the Kit gap log at %s", path)
