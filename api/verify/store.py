# Adapted from Azimlearning/Arcana-v2, api/labs/store.py @ 21c6dcf5. Read in full. Kept: put_verified takes only the minted type,
# re-checks the hash and the id, never replaces a stored row (INSERT OR IGNORE), get() returns nothing for a row whose hash no
# longer matches, and rejected sources are kept (capped) as an audit trail and never served. Dropped: the lifecycle table, delivery
# counts and promotion (P5); `state` here is only 'verified' or 'rejected'.
"""EnvironmentStore: verified Environments behind a small abstraction, with a local SQLite implementation.

The store holds what the verifier minted and what it refused. It is a record, not an authority: the delivery gate does not
trust it (see api/verify/gate.py), and `get_record` exists so the gate can read the row without the store's own checks.
"""

from __future__ import annotations

import hashlib
import hmac
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
    attestation: str | None = None


_COLUMNS = (
    "env_id, title, lane, label, kit_version, kit_sha256, html, html_sha256, citations, plan_summary, checked, state"
)


def attestation_for(key: bytes, record: StoredEnvironment) -> str:
    """HMAC-SHA256 over every field the delivery gate trusts (A-19). The key lives outside the data directory, so someone who can only write
    the SQLite file cannot make a row the gate accepts."""
    body = json.dumps(
        [
            record.env_id,
            record.title,
            record.lane,
            record.label,
            record.kit_version,
            record.kit_sha256,
            record.html_sha256,
            record.citations,
            record.plan_summary,
            record.checked,
        ],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hmac.new(key, body.encode("ascii"), hashlib.sha256).hexdigest()


class ConflictingRecord(ValueError):
    """The same HTML is already stored under a different claim (label, lane, citations or Kit). A stored Environment is never replaced; the caller decides what
    to do (the pipeline delivers the stored one through the gate)."""


class SqliteEnvironmentStore:
    def __init__(self, path: Path, attestation_key: bytes | None = None):
        self._path = path
        self._key = attestation_key or None
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS environments (env_id TEXT PRIMARY KEY, title TEXT NOT NULL, lane TEXT NOT NULL, "
                "label TEXT NOT NULL, kit_version TEXT NOT NULL, kit_sha256 TEXT NOT NULL, html TEXT NOT NULL, html_sha256 TEXT NOT NULL, "
                "citations TEXT NOT NULL, plan_summary TEXT NOT NULL, checked TEXT NOT NULL, state TEXT NOT NULL, "
                "reason TEXT, created_at TEXT NOT NULL)"
            )
            columns = {r[1] for r in db.execute("PRAGMA table_info(environments)")}
            if "attestation" not in columns:  # older stores: rows keep NULL and are unattested
                db.execute("ALTER TABLE environments ADD COLUMN attestation TEXT")
            # The library and lifecycle (P5). These tables hold decisions ABOUT stored Environments, never their content, so the verified rows stay immutable.
            db.execute(
                "CREATE TABLE IF NOT EXISTS lifecycle (env_id TEXT PRIMARY KEY, status TEXT NOT NULL, reason TEXT NOT NULL, changed_at TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS flags (id INTEGER PRIMARY KEY AUTOINCREMENT, env_id TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS questions (canon TEXT PRIMARY KEY, env_id TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            if "answer" not in {r[1] for r in db.execute("PRAGMA table_info(questions)")}:  # older stores: the written answer was not kept
                db.execute("ALTER TABLE questions ADD COLUMN answer TEXT")
            # The seeded library (D-42): which verified Environment serves which KSSM topic, and the Plan's own words to show with it. Decisions ABOUT stored
            # rows, like the tables above; the Environment itself stays in `environments` and is re-checked by the gate on every delivery.
            db.execute(
                "CREATE TABLE IF NOT EXISTS library_topics (topic TEXT NOT NULL, env_id TEXT NOT NULL, plan_id TEXT NOT NULL, title TEXT NOT NULL, "
                "goal TEXT NOT NULL, note TEXT NOT NULL, indexed_at TEXT NOT NULL, PRIMARY KEY (topic, env_id))"
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
            "grid_points": env.checked.grid_points,
            "reference_cases": env.checked.reference_cases,
            "models": [{"id": mid, "params": dict(params)} for mid, params in env.checked.models],
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
        if self._key is not None and stored.attestation is None:
            # Sign what the VERIFIER just minted, never what is in the row: if a row was planted before this call, the signature will not
            # match it and the gate refuses it (fail closed).
            minted = StoredEnvironment(
                env_id=env.env_id,
                title=env.title,
                lane=env.lane,
                label=env.label,
                kit_version=env.kit_version,
                kit_sha256=env.kit_sha256,
                html="",
                html_sha256=env.html_sha256,
                citations=[c.model_dump() for c in env.citations],
                plan_summary=env.plan_summary,
                checked=checked,
                state="verified",
            )
            with closing(self._connect()) as db, db:
                db.execute(
                    "UPDATE environments SET attestation = ? WHERE env_id = ? AND attestation IS NULL",
                    (attestation_for(self._key, minted), env.env_id),
                )
            stored = self.get(env.env_id) or stored
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
            raise ConflictingRecord(
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
                f"SELECT {_COLUMNS}, attestation FROM environments WHERE env_id = ? AND state = 'verified'", (env_id,)
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
            attestation=row[12],
        )

    def attestation_ok(self, record: StoredEnvironment) -> bool:
        """True when no key is configured (A-19 stays open and STATUS says so) or the row carries a valid signature."""
        if self._key is None:
            return True
        return record.attestation is not None and hmac.compare_digest(
            record.attestation, attestation_for(self._key, record)
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

    # ── library and lifecycle (P5) ──────────────────────────────────────────────────────────────────────────────────────────────

    def status(self, env_id: str) -> str:
        """`active` or `withdrawn`. A withdrawn Environment is never delivered (the gate checks), whatever its row says."""
        with closing(self._connect()) as db:
            row = db.execute("SELECT status FROM lifecycle WHERE env_id = ?", (env_id,)).fetchone()
        return "active" if row is None else str(row[0])

    def withdraw(self, env_id: str, reason: str) -> None:
        self._set_status(env_id, "withdrawn", reason)

    def restore(self, env_id: str) -> None:
        self._set_status(env_id, "active", "restored")

    def _set_status(self, env_id: str, status: str, reason: str) -> None:
        if self.get_record(env_id) is None:
            raise KeyError(f"no verified Environment '{env_id}'")
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO lifecycle (env_id, status, reason, changed_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(env_id) DO UPDATE SET status = excluded.status, reason = excluded.reason, changed_at = excluded.changed_at",
                (env_id, status, reason[:240], datetime.now(UTC).isoformat()),
            )

    def flag(self, env_id: str, note: str) -> int:
        """Record that someone thinks this Environment is wrong. Returns the number of flags it now has. Flags never change what is delivered by themselves."""
        if self.get_record(env_id) is None:
            raise KeyError(f"no verified Environment '{env_id}'")
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO flags (env_id, note, created_at) VALUES (?, ?, ?)",
                (env_id, note[:240], datetime.now(UTC).isoformat()),
            )
            return int(db.execute("SELECT COUNT(*) FROM flags WHERE env_id = ?", (env_id,)).fetchone()[0])

    def flag_notes(self, env_id: str, limit: int = 5) -> list[str]:
        """The most recent flag notes for an Environment, newest first."""
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT note FROM flags WHERE env_id = ? ORDER BY id DESC LIMIT ?", (env_id, limit)
            ).fetchall()
        return [str(r[0]) for r in rows]

    def flag_count(self, env_id: str) -> int:
        with closing(self._connect()) as db:
            return int(db.execute("SELECT COUNT(*) FROM flags WHERE env_id = ?", (env_id,)).fetchone()[0])

    def remember_question(self, canon: str, env_id: str, answer: str | None = None) -> None:
        """The question cache: the same canonical question gets the same Environment next time, with no model call. `answer` is the written answer that
        streamed with it, kept so a repeat needs no model call for the words either. Replaces an older entry."""
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO questions (canon, env_id, created_at, answer) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(canon) DO UPDATE SET env_id = excluded.env_id, created_at = excluded.created_at, answer = excluded.answer",
                (canon, env_id, datetime.now(UTC).isoformat(), answer),
            )

    def lookup_question(self, canon: str) -> str | None:
        entry = self.lookup_question_entry(canon)
        return None if entry is None else entry[0]

    def lookup_question_entry(self, canon: str) -> tuple[str, str | None] | None:
        """(env_id, the written answer kept with it or None) for a question asked before."""
        with closing(self._connect()) as db:
            row = db.execute("SELECT env_id, answer FROM questions WHERE canon = ?", (canon,)).fetchone()
        return None if row is None else (str(row[0]), None if row[1] is None else str(row[1]))

    def index_topic(self, topic: str, env_id: str, *, plan_id: str, title: str, goal: str, note: str) -> None:
        """Say that the verified Environment `env_id` serves `topic` (the seeded library, D-42). `note` is the hand-written Plan's own explanation, shown
        with it when it is served with no model call. Raises KeyError for an Environment that is not stored as verified."""
        if self.get_record(env_id) is None:
            raise KeyError(f"no verified Environment '{env_id}'")
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO library_topics (topic, env_id, plan_id, title, goal, note, indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(topic, env_id) DO UPDATE SET plan_id = excluded.plan_id, title = excluded.title, goal = excluded.goal, "
                "note = excluded.note, indexed_at = excluded.indexed_at",
                (topic, env_id, plan_id, title, goal, note, datetime.now(UTC).isoformat()),
            )

    def topic_entries(self, topic: str) -> list[dict]:
        """Every indexed Environment for `topic`, in a stable order. Whether one may be delivered is the gate's decision, not this list's."""
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT env_id, plan_id, title, goal, note FROM library_topics WHERE topic = ? ORDER BY plan_id, env_id", (topic,)
            ).fetchall()
        return [{"env_id": r[0], "plan_id": r[1], "title": r[2], "goal": r[3], "note": r[4]} for r in rows]

    def library(self, current_kit_sha: dict[str, str | None]) -> list[dict]:
        """One card per verified Environment, newest first. `current_kit_sha` maps a Kit version to the sha256 of its CURRENT build (None when not built);
        an Environment made with other bytes is `stale` and is not delivered until it is verified again."""
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT e.env_id, e.title, e.lane, e.label, e.kit_version, e.kit_sha256, e.checked, "
                "COALESCE(l.status, 'active'), (SELECT COUNT(*) FROM flags f WHERE f.env_id = e.env_id) "
                "FROM environments e LEFT JOIN lifecycle l ON l.env_id = e.env_id WHERE e.state = 'verified' ORDER BY e.created_at DESC"
            ).fetchall()
        cards = []
        for env_id, title, lane, label, kit_version, kit_sha, checked, status, flags in rows:
            data = json.loads(checked)
            cards.append(
                {
                    "id": env_id,
                    "title": title,
                    "lane": lane,
                    "label": label,
                    "kitVersion": kit_version,
                    "status": status,
                    "stale": current_kit_sha.get(kit_version) != kit_sha,
                    "flags": int(flags),
                    "models": [m["id"] for m in data.get("models", [])],
                }
            )
        return cards
