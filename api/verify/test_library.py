"""The library and lifecycle (P5): withdrawn Environments are never delivered, flags are recorded but change nothing by themselves, stale ones are
listed as stale, and the question cache returns the same Environment without a model call."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.verify.conftest import mint
from api.verify.gate import deliver
from api.verify.mint import VerificationFailed, kit_bundle_sha256
from api.verify.store import SqliteEnvironmentStore

ORIGIN = "http://localhost:3000"


@pytest.fixture
def stored(tmp_path: Path, kit_dist: Path) -> tuple[SqliteEnvironmentStore, str]:
    store = SqliteEnvironmentStore(tmp_path / "envs.db")
    env = mint(kit_dist)
    store.put_verified(env)
    return store, env.env_id


def test_a_withdrawn_environment_is_refused_by_the_gate_and_restoring_it_brings_it_back(stored, kit_dist: Path) -> None:  # noqa: ANN001
    store, env_id = stored
    assert deliver(store, env_id, public_origin=ORIGIN, kit_dist=kit_dist).id == env_id
    store.withdraw(env_id, "the label on the spring was wrong")
    assert store.status(env_id) == "withdrawn"
    with pytest.raises(VerificationFailed) as err:
        deliver(store, env_id, public_origin=ORIGIN, kit_dist=kit_dist)
    assert (err.value.stage, err.value.rule) == ("gate", "withdrawn")
    store.restore(env_id)
    assert deliver(store, env_id, public_origin=ORIGIN, kit_dist=kit_dist).id == env_id


def test_withdrawing_an_unknown_environment_is_an_error_not_a_silent_row(stored) -> None:  # noqa: ANN001
    store, _ = stored
    with pytest.raises(KeyError):
        store.withdraw("nope-000000000000", "x")
    with pytest.raises(KeyError):
        store.flag("nope-000000000000", "x")


def test_flags_are_counted_and_do_not_by_themselves_stop_delivery(stored, kit_dist: Path) -> None:  # noqa: ANN001
    store, env_id = stored
    assert store.flag(env_id, "the units look odd") == 1 and store.flag(env_id, "same here") == 2
    assert store.flag_count(env_id) == 2
    assert deliver(store, env_id, public_origin=ORIGIN, kit_dist=kit_dist).id == env_id


def test_the_library_lists_each_environment_once_with_its_status_flags_and_staleness(
    stored, kit_dist: Path, kit_version: str
) -> None:  # noqa: ANN001
    store, env_id = stored
    store.flag(env_id, "odd")
    (card,) = store.library({kit_version: kit_bundle_sha256(kit_dist, kit_version)})
    assert card["id"] == env_id and card["status"] == "active" and card["flags"] == 1 and card["stale"] is False
    assert card["models"] == ["mechanics.hookes"] and card["label"] == "model-checked"
    (stale,) = store.library({kit_version: "0" * 64})  # the Kit was rebuilt with other bytes
    assert stale["stale"] is True
    (gone,) = store.library({})  # the Kit version is not built at all
    assert gone["stale"] is True
    store.withdraw(env_id, "x")
    assert store.library({kit_version: kit_bundle_sha256(kit_dist, kit_version)})[0]["status"] == "withdrawn"


def test_the_question_cache_maps_a_canonical_question_to_an_environment_and_can_be_replaced(stored) -> None:  # noqa: ANN001
    store, env_id = stored
    assert store.lookup_question("why does a spring stretch") is None
    store.remember_question("why does a spring stretch", env_id)
    assert store.lookup_question("why does a spring stretch") == env_id
    store.remember_question("why does a spring stretch", "other-123")
    assert store.lookup_question("why does a spring stretch") == "other-123"


def test_lifecycle_tables_never_change_the_verified_rows(stored) -> None:  # noqa: ANN001
    store, env_id = stored
    before = store.get_record(env_id)
    store.withdraw(env_id, "x")
    store.flag(env_id, "y")
    store.restore(env_id)
    assert store.get_record(env_id) == before
