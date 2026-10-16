"""Fixtures for the verification tests. The Kit must be built; if its dist is missing the fixture builds it."""

from __future__ import annotations

from pathlib import Path

from api.kit import latest_version
from api.schema.generated import Citation
from api.verify.mint import VerifiedEnvironment, verify_environment

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "data" / "fixtures" / "envs"
ORIGIN = "http://localhost:3000"


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def mint(kit_dist: Path, name: str = "reference-spring.html", **overrides) -> VerifiedEnvironment:
    args = dict(
        slug="reference-spring",
        title="Why does a spring stretch?",
        raw_html=fixture_html(name),
        lane="instantiate",
        label="model-checked",
        kit_version=latest_version(kit_dist),
        citations=[Citation(source="UNVERIFIED (corpus not loaded until P2)", page=None, quote=None, verified=False)],
        plan_summary="A hand-written fixture.",
        public_origin=ORIGIN,
        kit_dist=kit_dist,
        interaction_seconds=1.0,
    )
    args.update(overrides)
    return verify_environment(**args)  # type: ignore[arg-type]
