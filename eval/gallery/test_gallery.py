"""The gallery builder writes every Environment as a hash-checked offline file and an index with no external requests."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from eval.gallery.build import build_gallery

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def gallery(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[dict]]:
    out = tmp_path_factory.mktemp("gallery")
    return out, build_gallery(out, corpus_path=None)


def test_one_file_per_plan_and_an_index(gallery: tuple[Path, list[dict]]) -> None:
    out, records = gallery
    plans = sorted(json.loads(p.read_text(encoding="utf-8"))["id"] for p in (REPO / "data" / "plans").glob("*.json"))
    assert sorted(r["id"] for r in records) == sorted(plans)
    index = (out / "index.html").read_text(encoding="utf-8")
    for r in records:
        assert f'href="{r["file"]}"' in index
        assert (out / r["file"]).exists()


def test_without_a_corpus_nothing_claims_a_source(gallery: tuple[Path, list[dict]]) -> None:
    out, records = gallery
    assert {r["label"] for r in records} == {"model-checked"}
    assert "kit-verified" not in (out / "index.html").read_text(encoding="utf-8").lower().replace("0 with a textbook source", "")


def test_the_index_loads_nothing_from_another_origin(gallery: tuple[Path, list[dict]]) -> None:
    index = (gallery[0] / "index.html").read_text(encoding="utf-8")
    assert "default-src 'none'" in index
    assert not re.search(r"(src|href)=\"(https?:)?//", index)
    assert "<script" not in index


def test_a_file_runs_offline_in_a_closed_sandbox(gallery: tuple[Path, list[dict]]) -> None:
    out, records = gallery
    path = out / records[0]["file"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(path.as_uri())
            page.wait_for_selector("#frame:not([hidden])", timeout=15000)
            assert page.get_attribute("#frame", "sandbox") == "allow-scripts"
        finally:
            browser.close()


def test_every_subject_and_form_has_a_chapter_pack_that_checks_every_fingerprint(gallery: tuple[Path, list[dict]]) -> None:
    out, _ = gallery
    expected: dict[str, int] = {}
    for path in (REPO / "data" / "plans").glob("*.json"):
        subject, form = json.loads(path.read_text(encoding="utf-8"))["topic"].split("_")[:2]
        expected[f"pack-{subject}-{form}.html"] = expected.get(f"pack-{subject}-{form}.html", 0) + 1
    assert sorted(p.name for p in out.glob("pack-*.html")) == sorted(expected)
    index = (out / "index.html").read_text(encoding="utf-8")
    for name, count in expected.items():
        text = (out / name).read_text(encoding="utf-8")
        assert text.count('<button type="button" data-open=') == count
        assert f'href="{name}"' in index
    biggest = max(expected, key=lambda n: expected[n])
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto((out / biggest).as_uri())
            page.wait_for_function("document.getElementById('state').textContent.startsWith('All ')", timeout=15000)
            assert page.inner_text("#state") == f"All {expected[biggest]} fingerprints checked."
        finally:
            browser.close()
