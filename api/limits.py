"""Request limits (hard constraint 12, the deploy gate): a per-client rate limit and a cap on questions in flight.

Both are in-process and per worker, which is right for the single-operator API (D-11). A multi-worker deploy needs the same limits at the proxy;
`refdocs/guides/checklist.md` says so. Neither reads the request body or the question.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

WINDOW_SECONDS = 60.0
SLOT_TTL_SECONDS = 600.0


class RateLimiter:
    """At most `per_minute` admissions per key in any sliding minute. `per_minute` of 0 admits everything."""

    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic):
        self._limit = per_minute
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self._limit <= 0:
            return True
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            if len(self._hits) > 4096:  # forget idle clients so the table cannot grow without bound
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= WINDOW_SECONDS]:
                    del self._hits[k]
            return True


class ConcurrencyGate:
    """At most `limit` slots held at once. A slot that is never released (a client that vanished before its stream started) expires."""

    def __init__(self, limit: int, clock: Callable[[], float] = time.monotonic):
        self._limit = limit
        self._clock = clock
        self._held: dict[int, float] = {}
        self._next = 0
        self._lock = threading.Lock()

    def acquire(self) -> int | None:
        """A slot token, or None when the server is full. `limit` of 0 always admits (token 0, nothing tracked)."""
        if self._limit <= 0:
            return 0
        now = self._clock()
        with self._lock:
            for token in [t for t, at in self._held.items() if now - at >= SLOT_TTL_SECONDS]:
                del self._held[token]
            if len(self._held) >= self._limit:
                return None
            self._next += 1
            self._held[self._next] = now
            return self._next

    def release(self, token: int) -> None:
        with self._lock:
            self._held.pop(token, None)

    def in_flight(self) -> int:
        with self._lock:
            return len(self._held)


class DailyLimiter:
    """At most `per_client` admissions per client address and `total` admissions overall in one UTC day. 0 turns a limit off. The deploy gate asks for per-session and
    per-day limits (D-11); there are no accounts, so a "session" is a client address, and the overall count is what keeps a crowd of addresses from running up a bill
    (the monthly spend cap in the LLM seam is the last stop, this is the earlier and gentler one). Counts reset at 00:00 UTC. In-process and per worker, like the others.
    A table that grows past `MAX_CLIENTS` in one day refuses new addresses (fail closed) instead of growing without bound."""

    MAX_CLIENTS = 50_000

    def __init__(self, per_client: int, total: int, clock: Callable[[], float] = time.time):
        self._per_client = per_client
        self._total = total
        self._clock = clock
        self._day = -1
        self._counts: dict[str, int] = defaultdict(int)
        self._all = 0
        self._lock = threading.Lock()

    def _roll(self) -> None:
        day = int(self._clock() // 86400)
        if day != self._day:
            self._day = day
            self._counts.clear()
            self._all = 0

    def allow(self, key: str) -> bool:
        if self._per_client <= 0 and self._total <= 0:
            return True
        with self._lock:
            self._roll()
            if self._total > 0 and self._all >= self._total:
                return False
            if self._per_client > 0:
                if key not in self._counts and len(self._counts) >= self.MAX_CLIENTS:
                    return False
                if self._counts[key] >= self._per_client:
                    return False
                self._counts[key] += 1
            self._all += 1
            return True

    def used_today(self) -> int:
        with self._lock:
            self._roll()
            return self._all
