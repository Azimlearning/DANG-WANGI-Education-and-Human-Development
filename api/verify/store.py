# Adapted from Azimlearning/Arcana-v2, api/labs/store.py @ 21c6dcf5. Read in full. Kept: put_verified takes only the minted type,
# re-checks the hash and the id, never replaces a stored row (INSERT OR IGNORE), get() returns nothing for a row whose hash no
# longer matches, and rejected sources are kept (capped) as an audit trail and never served. Dropped: the lifecycle table, delivery
# counts and promotion (P5); `state` here is only 'verified' or 'rejected'.
"""EnvironmentStore: verified Environments behind a small abstraction, with a local SQLite implementation.

The store holds what the verifier minted and what it refused. It is a record, not an authority: the delivery gate does not
trust it (see api/verify/gate.py), and `get_record` exists so the gate can read the row without the store's own checks.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from api.verify.mint import VerifiedEnvironment, env_id_for, html_sha256

MAX_REJECTED_HTML_CHARS = 20_000


@dataclass(frozen=True)
class StoredEnvironment:
    """A record, not an artifact: the delivery path never accepts this type."""

    env_id: str
    title: str
    lane: str
    label: str
    kit_version: str
    kit_sha256: str
    html: str
    html_sha256: str
    citations: list[dict]
    plan_summary: str
    checked: dict
    state: str


_COLUMNS = (
    "env_id, title, lane, label, kit_version, kit_sha256, html, html_sha256, citations, plan_summary, checked, state"
)


class SqliteEnvironmentStore:
    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS environments (env_id TEXT PRIMARY KEY, title TEXT NOT NULL, lane TEXT NOT NULL, "
                "label TEXT NOT NULL, kit_version TEXT NOT NULL, kit_sha256 TEXT NOT NULL, html TEXT NOT NULL, html_sha256 TEXT NOT NULL, "
                "citations TEXT NOT NULL, plan_summary TEXT NOT NULL, checked TEXT NOT NULL, state TEXT NOT NULL, "
                "reason TEXT, created_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def put_verified(self, env: VerifiedEnvironment) -> StoredEnvironment:
        if not isinstance(env, VerifiedEnvironment):
            raise TypeError("only a VerifiedEnvironment can be stored as verified")
        if html_sha256(env.html) != env.html_sha256:
            raise ValueError("the environment's HTML does not match its hash")
        if not env.env_id.endswith(env.html_sha256[:12]):
            raise ValueError("the environment's id is not the one its hash gives")
        checked = {
            "layers": list(env.checked.layers),
            "controls_exercised": env.checked.controls_exercised,
            "readouts": env.checked.readouts,
            "interaction_seconds": env.checked.interaction_seconds,
        }
        with closing(self._connect()) as db, db:
            # OR IGNORE: the same id is the same HTML, and a stored Environment is never replaced
            db.execute(
                f"INSERT OR IGNORE INTO environments ({_COLUMNS}, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'verified', NULL, ?)",
                (
                    env.env_id,
                    env.title,
                    env.lane,
                    env.label,
                    env.kit_version,
                    env.kit_sha256,
                    env.html,
                    env.html_sha256,
                    json.dumps([c.model_dump() for c in env.citations]),
                    env.plan_summary,
                    json.dumps(checked),
                    datetime.now(UTC).isoformat(),
                ),
            )
        stored = self.get(env.env_id)
        if stored is None:
            raise ValueError("the environment could not be stored")
        # The id is a hash of the HTML alone, so the same HTML verified again under a different label, lane, citations or Kit would
        # silently return the OLD row. Refuse instead: a changed claim about the same bytes needs a deliberate new record.
        new = (
            env.title,
            env.lane,
            env.label,
            env.kit_version,
            env.kit_sha256,
            json.dumps([c.model_dump() for c in env.citations]),
            env.plan_summary,
        )
        old = (
            stored.title,
            stored.lane,
            stored.label,
            stored.kit_version,
            stored.kit_sha256,
            json.dumps(stored.citations),
            stored.plan_summary,
        )
        if new != old:
            raise ValueError(
                "this HTML is already stored with different metadata (label, lane, citations or Kit); it is never replaced"
            )
        return stored

    def put_rejected(self, slug: str, raw_html: str, stage: str, rule: str, reason: str) -> None:
        sha = html_sha256(raw_html)
        with closing(self._connect()) as db, db:
            db.execute(
                f"INSERT OR IGNORE INTO environments ({_COLUMNS}, reason, created_at) VALUES (?, ?, '', '', '', '', ?, ?, '[]', '', '{{}}', 'rejected', ?, ?)",
                (
                    f"rejected-{env_id_for(slug, sha)}",
                    slug,
                    raw_html[:MAX_REJECTED_HTML_CHARS],
                    sha,
                    f"{stage}/{rule}: {reason}"[:300],
                    datetime.now(UTC).isoformat(),
                ),
            )

    def latest_id(self, slug: str) -> str | None:
        """The newest verified Environment id made from `slug` (ids are `<slug>-<12 hex>`), or None."""
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT env_id FROM environments WHERE state = 'verified' AND env_id LIKE ? ESCAPE '\\' "
                "ORDER BY created_at DESC LIMIT 1",
                (slug.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "-%",),
            ).fetchone()
        return None if row is None else str(row[0])

    def get_record(self, env_id: str) -> StoredEnvironment | None:
        """The verified row exactly as stored, with no integrity check. For the delivery gate, which does its own."""
        with closing(self._connect()) as db:
            row = db.execute(
                f"SELECT {_COLUMNS} FROM environments WHERE env_id = ? AND state = 'verified'", (env_id,)
            ).fetchone()
        if row is None:
            return None
        return StoredEnvironment(
            env_id=row[0],
            title=row[1],
            lane=row[2],
            label=row[3],
            kit_version=row[4],
            kit_sha256=row[5],
            html=row[6],
            html_sha256=row[7],
            citations=json.loads(row[8]),
            plan_summary=row[9],
            checked=json.loads(row[10]),
            state=row[11],
        )

    def get(self, env_id: str) -> StoredEnvironment | None:
        """A verified Environment by id, or None (a rejected one is never returned, nor a row whose HTML no longer matches)."""
        record = self.get_record(env_id)
        if record is None:
            return None
        if html_sha256(record.html) != record.html_sha256 or not record.env_id.endswith(record.html_sha256[:12]):
            return None  # an edited row is not an Environment
        return record

    def rejected(self) -> list[dict[str, str]]:
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT title, html_sha256, reason FROM environments WHERE state = 'rejected' ORDER BY created_at"
            ).fetchall()
        return [{"slug": r[0], "html_sha256": r[1], "reason": r[2]} for r in rows]

    def counts(self) -> dict[str, int]:
        with closing(self._connect()) as db:
            rows = db.execute("SELECT state, COUNT(*) FROM environments GROUP BY state").fetchall()
        return {str(state): int(n) for state, n in rows}
