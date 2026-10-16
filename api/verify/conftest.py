"""Fixtures for the verification tests. The Kit must be built; if its dist is missing the fixture builds it."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from api.schema.generated import Citation
from api.verify.mint import VerifiedEnvironment, verify_environment

REPO = Path(__file__).resolve().parents[2]
KIT_DIST = REPO / "packages" / "kit" / "dist"
FIXTURES = REPO / "data" / "fixtures" / "envs"
ORIGIN = "http://localhost:3000"


@pytest.fixture(scope="session")
def kit_dist() -> Path:
    if not (KIT_DIST / "0.0.1" / "core.js").is_file():
        pnpm = shutil.which("pnpm")
        if pnpm is None:
            pytest.fail("the Kit is not built and pnpm is not available; run `pnpm --filter @synapse/kit build`")
        subprocess.run([pnpm, "--filter", "@synapse/kit", "build"], cwd=REPO, check=True)
    return KIT_DIST


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def mint(kit_dist: Path, name: str = "reference-spring.html", **overrides) -> VerifiedEnvironment:
    args = dict(
        slug="reference-spring",
        title="Why does a spring stretch?",
        raw_html=fixture_html(name),
        lane="instantiate",
        label="dev-fixture",
        kit_version="0.0.1",
        citations=[Citation(source="UNVERIFIED (corpus not loaded until P2)", page=None, quote=None, verified=False)],
        plan_summary="A hand-written fixture.",
        public_origin=ORIGIN,
        kit_dist=kit_dist,
        interaction_seconds=1.0,
    )
    args.update(overrides)
    return verify_environment(**args)  # type: ignore[arg-type]
