"""Repo-wide test guard: no test may reach a machine other than this one.

A paid provider is now wired in live mode, and a test that sets a (dummy) key would send a real request to the real API: that happened once on
2026-10-18 when a live-mode route test met the new Anthropic provider (a 401 came back from api.anthropic.com; nothing was billed). This guard makes
that impossible to repeat by accident: connecting to, or resolving, anything but a loopback host raises. Tests that need a provider use a mock
transport; the stricter `no_network` fixture in api/conftest.py still forbids even loopback connections where a test says so.
"""

from __future__ import annotations

import socket

import pytest

from api.core.settings import Settings

_LOOPBACK = {"localhost", "127.0.0.1", "::1", "0.0.0.0", ""}  # noqa: S104 - a name to allow, not an address to bind


def _host(address: object) -> str | None:
    if isinstance(address, tuple) and address:
        return str(address[0])
    return None


@pytest.fixture(autouse=True)
def _no_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def refuse(what: str) -> None:
        raise AssertionError(f"a test tried to reach {what}: tests may only use this machine (loopback); mock the provider instead")

    def connect(self: socket.socket, address: object, *args: object, **kwargs: object) -> None:
        host = _host(address)
        if host is not None and host not in _LOOPBACK:
            refuse(host)
        return real_connect(self, address, *args, **kwargs)  # type: ignore[arg-type]

    def connect_ex(self: socket.socket, address: object, *args: object, **kwargs: object) -> int:
        host = _host(address)
        if host is not None and host not in _LOOPBACK:
            refuse(host)
        return real_connect_ex(self, address, *args, **kwargs)  # type: ignore[arg-type]

    def getaddrinfo(host: object, *args: object, **kwargs: object):  # noqa: ANN202
        if host is not None and str(host) not in _LOOPBACK:
            refuse(str(host))
        return real_getaddrinfo(host, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


@pytest.fixture(autouse=True)
def _ignore_the_developers_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Settings` reads `.env` by default, so a test written for "no key configured" would pass or fail depending on whose machine it runs on, and would
    carry a real key into the test process (it surfaced on 2026-10-18 the day the owner created `.env`). No test sees the file. A test that wants a file
    passes `_env_file=` itself; the process environment is cleared separately by `clean_env` in api/conftest.py."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
