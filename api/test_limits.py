from __future__ import annotations

from api.limits import SLOT_TTL_SECONDS, WINDOW_SECONDS, ConcurrencyGate, DailyLimiter, RateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_the_rate_limiter_admits_up_to_the_limit_per_client_per_minute_then_recovers() -> None:
    clock = Clock()
    limiter = RateLimiter(3, clock)
    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("b") is True  # another client is unaffected
    clock.now += WINDOW_SECONDS - 1
    assert limiter.allow("a") is False
    clock.now += 1.5
    assert limiter.allow("a") is True


def test_a_limit_of_zero_turns_the_limiter_off() -> None:
    limiter = RateLimiter(0)
    assert all(limiter.allow("a") for _ in range(100))


def test_the_rate_limiter_forgets_idle_clients() -> None:
    clock = Clock()
    limiter = RateLimiter(1, clock)
    for i in range(5000):
        limiter.allow(f"c{i}")
    clock.now += WINDOW_SECONDS + 1
    limiter.allow("fresh")
    assert len(limiter._hits) < 4096  # noqa: SLF001


def test_the_gate_holds_at_most_limit_slots_and_release_frees_one() -> None:
    gate = ConcurrencyGate(2)
    a, b = gate.acquire(), gate.acquire()
    assert a and b and gate.acquire() is None and gate.in_flight() == 2
    gate.release(a)  # type: ignore[arg-type]
    assert gate.acquire() is not None


def test_a_slot_that_is_never_released_expires() -> None:
    clock = Clock()
    gate = ConcurrencyGate(1, clock)
    assert gate.acquire() is not None and gate.acquire() is None
    clock.now += SLOT_TTL_SECONDS + 1
    assert gate.acquire() is not None


def test_a_gate_limit_of_zero_always_admits_and_tracks_nothing() -> None:
    gate = ConcurrencyGate(0)
    assert [gate.acquire() for _ in range(10)] == [0] * 10 and gate.in_flight() == 0


DAY = 86400.0


def test_the_daily_limiter_admits_up_to_the_limit_per_client_per_day_then_recovers_at_midnight_utc() -> None:
    clock = Clock()
    clock.now = 10 * DAY + 100
    limiter = DailyLimiter(3, 0, clock)
    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("b") is True  # another client is unaffected
    clock.now = 11 * DAY - 1
    assert limiter.allow("a") is False  # still the same UTC day
    clock.now = 11 * DAY + 1
    assert limiter.allow("a") is True


def test_the_overall_daily_limit_stops_a_crowd_of_addresses() -> None:
    clock = Clock()
    limiter = DailyLimiter(0, 3, clock)
    assert [limiter.allow(f"c{i}") for i in range(5)] == [True, True, True, False, False]
    assert limiter.used_today() == 3


def test_a_refused_question_does_not_use_up_the_day() -> None:
    clock = Clock()
    limiter = DailyLimiter(1, 5, clock)
    assert limiter.allow("a") is True
    assert [limiter.allow("a") for _ in range(10)] == [False] * 10
    assert limiter.used_today() == 1


def test_both_daily_limits_at_zero_turn_it_off() -> None:
    limiter = DailyLimiter(0, 0)
    assert all(limiter.allow("a") for _ in range(1000))


def test_a_flood_of_new_addresses_in_one_day_is_refused_instead_of_growing_the_table(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(DailyLimiter, "MAX_CLIENTS", 3)
    limiter = DailyLimiter(5, 0, Clock())
    assert [limiter.allow(f"c{i}") for i in range(5)] == [True, True, True, False, False]
    assert limiter.allow("c0") is True  # a known client still gets in
