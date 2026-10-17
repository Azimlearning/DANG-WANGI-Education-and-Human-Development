"""The repo-wide guard in conftest.py: tests may talk to this machine and to nothing else."""

from __future__ import annotations

import socket

import httpx
import pytest

from api.llm.providers.anthropic import AnthropicProvider
from api.llm.types import LLMRequest


def test_a_connection_to_another_machine_is_refused() -> None:
    with socket.socket() as s, pytest.raises(AssertionError, match="tests may only use this machine"):
        s.connect(("203.0.113.7", 443))  # TEST-NET-3: never routable, so this cannot reach anything even if the guard failed


def test_resolving_a_public_name_is_refused() -> None:
    with pytest.raises(AssertionError, match="api.anthropic.com"):
        socket.getaddrinfo("api.anthropic.com", 443)


def test_loopback_still_works() -> None:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    with socket.socket() as client:
        client.connect(server.getsockname())
    server.close()


async def test_a_real_anthropic_provider_cannot_send_a_request_from_a_test() -> None:
    """The 2026-10-18 incident: a dummy key plus the live provider sent a real request. Now the call dies at name resolution. It dies LOUDLY: the guard's
    AssertionError is not an httpx error, so the provider cannot turn it into a 'transient' failure that a fallback or a retry would hide."""
    provider = AnthropicProvider("not-a-real-key", client=httpx.AsyncClient(timeout=5))
    with pytest.raises(AssertionError, match="api.anthropic.com"):
        await provider.complete(LLMRequest(prompt="x", purpose="explain", max_tokens=5), "claude-haiku-5-5")
