# Adapted from Azimlearning/Arcana-v2, api/llm/ledger.py @ 21c6dcf5. Read in full. Changes: stdlib logging, this repo's
# SpendCapExceeded, and a ledger that lives at data/ledger.db by default (see Settings.resolved_ledger_path).
"""The spend ledger: every paid call is written here, and the monthly cap is enforced from it.

Callers go through reserve() then settle(): reserve() refuses, before anything is sent, if the month's recorded spend plus
calls already in flight plus this call's worst case would exceed the cap (hard constraint 8).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Column, Engine, Float, Integer, MetaData, String, Table, create_engine, func, insert, select

from api.core.errors import SpendCapExceeded

log = logging.getLogger(__name__)

metadata = MetaData()

spend_ledger = Table(
    "spend_ledger",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", String, nullable=False),
    Column("month", String, nullable=False, index=True),
    Column("provider", String, nullable=False),
    Column("model", String, nullable=False),
    Column("tokens_in", Integer, nullable=False),
    Column("tokens_out", Integer, nullable=False),
    Column("cost_usd", Float, nullable=False),
    Column("purpose", String, nullable=False),
    Column("status", String, nullable=False),  # "ok" or "failed" (failed attempts cost nothing)
)


def engine_for(path: Path) -> Engine:
    """A SQLite engine at `path`, creating the parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


@dataclass(frozen=True)
class Reservation:
    estimate_usd: float


class SpendLedger:
    def __init__(
        self,
        engine: Engine,
        monthly_cap_usd: float | None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._engine = engine
        self._cap = monthly_cap_usd
        self._clock = clock
        self._lock = threading.Lock()
        self._pending = 0.0
        metadata.create_all(engine)

    def month_total(self) -> float:
        month = self._clock().strftime("%Y-%m")
        with self._engine.connect() as conn:
            total = conn.execute(
                select(func.coalesce(func.sum(spend_ledger.c.cost_usd), 0.0)).where(spend_ledger.c.month == month)
            ).scalar_one()
        return float(total)

    def summary(self) -> dict:
        """This month's spend for the operator: total, cap, what remains, and the split by purpose and by model. No prompt or reply text is ever stored."""
        month = self._clock().strftime("%Y-%m")
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    spend_ledger.c.purpose,
                    spend_ledger.c.model,
                    spend_ledger.c.status,
                    func.count(),
                    func.sum(spend_ledger.c.cost_usd),
                    func.sum(spend_ledger.c.tokens_in),
                    func.sum(spend_ledger.c.tokens_out),
                )
                .where(spend_ledger.c.month == month)
                .group_by(spend_ledger.c.purpose, spend_ledger.c.model, spend_ledger.c.status)
            ).all()
        by_purpose: dict[str, float] = {}
        by_model: dict[str, float] = {}
        calls = failed = 0
        for purpose, model, status, n, cost, _tin, _tout in rows:
            by_purpose[purpose] = by_purpose.get(purpose, 0.0) + float(cost or 0.0)
            by_model[model] = by_model.get(model, 0.0) + float(cost or 0.0)
            calls += int(n)
            failed += int(n) if status == "failed" else 0
        return {
            "month": month,
            "spent_usd": round(self.month_total(), 6),
            "cap_usd": self._cap,
            "remaining_usd": None if self._cap is None else round(self.remaining_usd() or 0.0, 6),
            "calls": calls,
            "failed_calls": failed,
            "by_purpose": {k: round(v, 6) for k, v in sorted(by_purpose.items())},
            "by_model": {k: round(v, 6) for k, v in sorted(by_model.items())},
        }

    def remaining_usd(self) -> float | None:
        """Cap minus this month's spend and in-flight reservations; None when there is no cap."""
        if self._cap is None:
            return None
        with self._lock:
            return max(self._cap - self.month_total() - self._pending, 0.0)

    def reserve(self, estimate_usd: float) -> Reservation:
        """Claim budget for one call, or raise SpendCapExceeded. Call before the provider."""
        with self._lock:
            if self._cap is not None:
                spent = self.month_total()
                if spent + self._pending + estimate_usd > self._cap:
                    log.warning(
                        "spend_cap_refused cap_usd=%s spent_usd=%.6f in_flight_usd=%.6f estimate_usd=%.6f",
                        self._cap,
                        spent,
                        self._pending,
                        estimate_usd,
                    )
                    raise SpendCapExceeded(
                        f"Monthly LLM cap of ${self._cap:.2f} would be exceeded "
                        f"(${spent:.4f} spent this month, this call may cost up to "
                        f"${estimate_usd:.4f}). The call was not sent."
                    )
            self._pending += estimate_usd
            return Reservation(estimate_usd)

    def settle(
        self,
        reservation: Reservation,
        *,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        purpose: str,
        status: str = "ok",
    ) -> None:
        """Release the reservation and record what actually happened."""
        now = self._clock()
        with self._lock:
            self._pending = max(self._pending - reservation.estimate_usd, 0.0)
            with self._engine.begin() as conn:
                conn.execute(
                    insert(spend_ledger).values(
                        ts=now.isoformat(),
                        month=now.strftime("%Y-%m"),
                        provider=provider,
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost_usd,
                        purpose=purpose,
                        status=status,
                    )
                )
        log.info(
            "spend_recorded provider=%s model=%s purpose=%s status=%s tokens_in=%d tokens_out=%d cost_usd=%.6f",
            provider,
            model,
            purpose,
            status,
            tokens_in,
            tokens_out,
            cost_usd,
        )

    def rows(self) -> list[dict]:
        with self._engine.connect() as conn:
            result = conn.execute(select(spend_ledger).order_by(spend_ledger.c.id))
            return [dict(r._mapping) for r in result]
