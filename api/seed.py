"""Verify the hand-written reference Environment and store it, so /ask has something to deliver on fakes.

Run: `uv run python -m api.seed`. It launches headless Chromium (the full render check, about 15 seconds) and writes
`<DATA_DIR>/environments.db`. The reference Environment is a walking-skeleton illustration, not the first vertical (D-09).
"""

from __future__ import annotations

import json

from api.core.settings import Settings, load_settings
from api.schema.generated import Citation
from api.verify.mint import verify_environment
from api.verify.render import INTERACTION_SECONDS
from api.verify.store import SqliteEnvironmentStore

REFERENCE_SLUG = "reference-spring"


def store_path(settings: Settings):
    return settings.data_dir / "environments.db"


def open_store(settings: Settings) -> SqliteEnvironmentStore:
    key = settings.store_attestation_key
    return SqliteEnvironmentStore(
        store_path(settings), key.get_secret_value().encode("utf-8") if key is not None else None
    )


def seed_reference(settings: Settings, interaction_seconds: float | None = None) -> str:
    fixtures = settings.data_dir / "fixtures" / "envs"
    plan = json.loads((fixtures / f"{REFERENCE_SLUG}.plan.json").read_text(encoding="utf-8"))
    env = verify_environment(
        slug=plan["id"],
        title=plan["title"],
        raw_html=(fixtures / f"{REFERENCE_SLUG}.html").read_text(encoding="utf-8"),
        lane=plan["lane"],
        label=plan["label"],
        kit_version=plan["kitVersion"],
        citations=[Citation.model_validate(c) for c in plan["citations"]],
        plan_summary=plan["planSummary"],
        public_origin=settings.public_origin,
        kit_dist=settings.kit_dist_dir,
        plan_models=plan.get("models"),
        interaction_seconds=INTERACTION_SECONDS if interaction_seconds is None else interaction_seconds,
    )
    open_store(settings).put_verified(env)
    return env.env_id


if __name__ == "__main__":
    print(seed_reference(load_settings()))
