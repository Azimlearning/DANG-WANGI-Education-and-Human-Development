from __future__ import annotations

from api.limits import SLOT_TTL_SECONDS, WINDOW_SECONDS, ConcurrencyGate, RateLimiter


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
