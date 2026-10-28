"""Bahasa Melayu through the API (W12, D-62): a translation is another verified Environment, linked to the English one. A draft is served only when the server is set to show
drafts; a reviewed one is always served; both come through the same delivery gate as any Environment."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import kitmanifest
from api.app import create_app
from api.core.settings import Settings
from api.i18n import overlay as ov
from api.kit import latest_version
from api.pipeline import library
from api.seed import open_store
from api.verify.mint import html_sha256


def _settings(data_dir: Path, kit_dist: Path, **extra) -> Settings:  # noqa: ANN003
    return Settings(_env_file=None, data_dir=data_dir, kit_dist_dir=kit_dist, verify_interaction_seconds=1.0, **extra)  # type: ignore[call-arg]


@pytest.fixture(scope="module")
def seeded(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, str, str]:
    """One English Environment and its Malay translation, built once in a real browser: (data dir, kit dist, English id, Malay id)."""
    kit = Path(__file__).resolve().parents[2] / "packages" / "kit" / "dist"
    data = tmp_path_factory.mktemp("data")
    settings = _settings(data, kit)
    store = open_store(settings)
    built = library.seed(
        store, kit_dist=kit, public_origin=settings.public_origin, interaction_seconds=1.0, only={"ohm_explorer"}, translations_dir=ov.OVERLAYS
    )
    (_, english) = built[0]
    translations = store.translations_of(english.env_id)
    assert len(translations) == 1 and translations[0]["status"] == "draft"
    return data, kit, english.env_id, translations[0]["envId"]


def test_with_drafts_turned_off_a_draft_translation_is_neither_listed_nor_served(seeded: tuple[Path, Path, str, str]) -> None:
    data, kit, english, malay = seeded
    client = TestClient(create_app(_settings(data, kit, bm_show_drafts=False)))
    assert client.get(f"/library/{english}/translations").json() == {"translations": []}
    assert client.get(f"/library/{malay}").status_code == 404
    assert client.get(f"/library/{malay}/export").status_code == 404
    assert client.get(f"/library/{english}").status_code == 200  # the English one is untouched


def test_by_default_drafts_are_shown_and_the_translation_comes_through_the_gate(seeded: tuple[Path, Path, str, str]) -> None:
    data, kit, english, malay = seeded
    client = TestClient(create_app(_settings(data, kit, bm_show_drafts=True)))
    listed = client.get(f"/library/{english}/translations").json()["translations"]
    assert listed == [{"lang": "ms", "envId": malay, "status": "draft", "reviewer": None, "reviewedOn": None}]
    block = client.get(f"/library/{malay}").json()
    assert block["title"] == "Hukum Ohm: arus, beza keupayaan dan rintangan"
    assert block["htmlSha256"] == html_sha256(block["html"])  # the browser re-hashes this before it renders
    assert '<html lang="ms">' in block["html"]
    assert block["label"] == client.get(f"/library/{english}").json()["label"]  # the trust label says nothing about the language
    assert client.get(f"/library/{malay}/export").status_code == 200


def test_a_reviewed_translation_is_served_with_drafts_turned_off(seeded: tuple[Path, Path, str, str]) -> None:
    data, kit, english, malay = seeded
    store = open_store(_settings(data, kit))
    store.link_translation(english, malay, lang="ms", status="reviewed", reviewer="Cikgu Aminah", reviewed_on="2026-11-03")
    try:
        client = TestClient(create_app(_settings(data, kit, bm_show_drafts=False)))
        listed = client.get(f"/library/{english}/translations").json()["translations"]
        assert listed[0]["status"] == "reviewed" and listed[0]["reviewer"] == "Cikgu Aminah"
        assert client.get(f"/library/{malay}").status_code == 200
    finally:
        store.link_translation(english, malay, lang="ms", status="draft", reviewer=None, reviewed_on=None)


def test_the_library_list_says_which_card_is_a_translation(seeded: tuple[Path, Path, str, str]) -> None:
    data, kit, english, malay = seeded
    cards = {c["id"]: c for c in TestClient(create_app(_settings(data, kit))).get("/library").json()["environments"]}
    assert cards[malay]["translationOf"] == english
    assert cards[english]["translationOf"] is None


def test_a_withdrawn_translation_is_not_listed(seeded: tuple[Path, Path, str, str]) -> None:
    data, kit, english, malay = seeded
    store = open_store(_settings(data, kit))
    client = TestClient(create_app(_settings(data, kit, bm_show_drafts=True)))
    store.withdraw(malay, "test")
    try:
        assert client.get(f"/library/{english}/translations").json() == {"translations": []}
        assert client.get(f"/library/{malay}").status_code >= 400
    finally:
        store.restore(malay)


def test_a_translation_cannot_be_linked_as_reviewed_without_a_reviewer(seeded: tuple[Path, Path, str, str]) -> None:
    data, kit, english, malay = seeded
    store = open_store(_settings(data, kit))
    with pytest.raises(ValueError, match="reviewer"):
        store.link_translation(english, malay, lang="ms", status="reviewed", reviewer=None, reviewed_on=None)
    with pytest.raises(ValueError, match="draft or reviewed"):
        store.link_translation(english, malay, lang="ms", status="approved", reviewer="x", reviewed_on="2026-11-03")


def test_the_manifest_the_planner_sees_is_unchanged_by_translations() -> None:
    kit = Path(__file__).resolve().parents[2] / "packages" / "kit" / "dist"
    manifest = kitmanifest.load(kit, latest_version(kit))
    assert "lang" in manifest.components["environment"]["signature"]
