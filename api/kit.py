"""Which Kit versions are built. The API never imports Kit source (the surfaces share only generated artefacts); it reads the build."""

from __future__ import annotations

import re
from pathlib import Path

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def built_versions(kit_dist: Path) -> list[str]:
    """Every built version (a folder holding core.js), oldest first."""
    if not kit_dist.is_dir():
        return []
    found = [d.name for d in kit_dist.iterdir() if _SEMVER.match(d.name) and (d / "core.js").is_file()]
    return sorted(found, key=lambda v: tuple(int(x) for x in v.split(".")))


def latest_version(kit_dist: Path) -> str:
    """The newest built Kit version. Raises FileNotFoundError when none is built (run `pnpm --filter @synapse/kit build`)."""
    versions = built_versions(kit_dist)
    if not versions:
        raise FileNotFoundError(f"no Kit is built in {kit_dist}; run `pnpm --filter @synapse/kit build`")
    return versions[-1]
