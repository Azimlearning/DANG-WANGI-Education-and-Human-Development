"""Shared fixtures. `no_network` makes any attempt to open a socket connection fail loudly."""

from __future__ import annotations

import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from api.kit import built_versions, latest_version

REPO = Path(__file__).resolve().parents[1]
KIT_DIST = REPO / "packages" / "kit" / "dist"


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted in a test that forbids it")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every setting from the process environment so a developer's shell cannot leak into a test."""
    for name in (
        "SYNAPSE_LLM_MODE",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "LLM_MONTHLY_CAP_USD",
        "PUBLIC_ORIGIN",
        "DATA_DIR",
        "KIT_DIST_DIR",
        "LEDGER_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(scope="session")
def kit_dist() -> Path:
    if not built_versions(KIT_DIST):
        pnpm = shutil.which("pnpm")
        if pnpm is None:
            pytest.fail("the Kit is not built and pnpm is not available; run `pnpm --filter @synapse/kit build`")
        subprocess.run([pnpm, "--filter", "@synapse/kit", "build"], cwd=REPO, check=True)
    return KIT_DIST


@pytest.fixture(scope="session")
def kit_version(kit_dist: Path) -> str:
    """The newest built Kit version, so a Kit bump does not mean editing tests."""
    return latest_version(kit_dist)
