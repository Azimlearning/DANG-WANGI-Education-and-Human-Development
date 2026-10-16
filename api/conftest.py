"""Shared fixtures. `no_network` makes any attempt to open a socket connection fail loudly."""

from __future__ import annotations

import socket

import pytest


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted in a test that forbids it")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every setting from the process environment so a developer's shell cannot leak into a test."""
    for name in (
        "SYNAPSE_LLM_MODE",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "LLM_MONTHLY_CAP_USD",
        "PUBLIC_ORIGIN",
        "DATA_DIR",
        "LEDGER_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
