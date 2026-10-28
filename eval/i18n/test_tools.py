"""The reviewer's workflow (W12, D-62): export a sheet, take corrections back, and flip a translation to reviewed only when every row is approved."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from api.i18n import overlay as ov
from eval.i18n import tools


@pytest.fixture(autouse=True)
def _isolated_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test here may touch the real page strings or the real Kit review record: they are copied, and the copies are what the tools read and write."""
    from api.i18n import kitwords

    web = tmp_path / "web_strings.json"
    shutil.copy(tools.WEB_STRINGS, web)
    monkeypatch.setattr(tools, "WEB_STRINGS", web)
    record = tmp_path / "kit_record.json"
    shutil.copy(kitwords.RECORD, record)
    monkeypatch.setattr(kitwords, "RECORD", record)


@pytest.fixture
def copy_of_overlays(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "ms"
    target.mkdir()
    for name in ("hookes_amali.json", "ohm_explorer.json"):
        shutil.copy(ov.OVERLAYS / name, target / name)
    monkeypatch.setattr(ov, "OVERLAYS", target)
    return target


def test_the_sheet_lists_every_place_with_the_english_beside_the_malay(copy_of_overlays: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = tools.all_plans
    monkeypatch.setattr(tools, "all_plans", lambda: [(p, plan) for p, plan in original() if plan.id in {"hookes_amali", "ohm_explorer"}])
    out = tmp_path / "review.csv"
    tools.sheet(out)
    rows = list(csv.DictReader(out.open(encoding="utf-8", newline="")))
    assert {r["plan"] for r in rows if not r["plan"].startswith("_")} == {"hookes_amali", "ohm_explorer"}
    title = next(r for r in rows if r["plan"] == "hookes_amali" and r["place"] == "/title")
    assert title["english"].startswith("Hooke") and title["malay"].startswith("Hukum Hooke") and title["approved"] == ""


def test_a_plan_becomes_reviewed_only_when_every_row_is_approved_and_corrections_are_kept(
    copy_of_overlays: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = tools.all_plans
    monkeypatch.setattr(tools, "all_plans", lambda: [(p, plan) for p, plan in original() if plan.id in {"hookes_amali", "ohm_explorer"}])
    out = tmp_path / "review.csv"
    tools.sheet(out)
    rows = list(csv.DictReader(out.open(encoding="utf-8", newline="")))
    for r in rows:
        r["approved"] = "yes"
    rows = [r for r in rows if not r["plan"].startswith("_")]
    ohm = [r for r in rows if r["plan"] == "ohm_explorer"]
    ohm[0]["approved"] = ""  # one row not approved: the whole Plan stays a draft
    hooke_title = next(r for r in rows if r["plan"] == "hookes_amali" and r["place"] == "/title")
    hooke_title["malay"] = "Hukum Hooke: bagaimana spring meregang?"  # the reviewer's correction
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["plan", "place", "english", "malay", "approved"])
        w.writeheader()
        w.writerows(rows)
    assert tools.import_sheet(out, "Cikgu Aminah", "2026-11-03") == 0
    hooke = json.loads((copy_of_overlays / "hookes_amali.json").read_text(encoding="utf-8"))
    ohm_file = json.loads((copy_of_overlays / "ohm_explorer.json").read_text(encoding="utf-8"))
    assert hooke["status"] == "reviewed" and hooke["reviewer"] == "Cikgu Aminah" and hooke["reviewed_on"] == "2026-11-03"
    assert hooke["strings"]["/title"] == "Hukum Hooke: bagaimana spring meregang?"
    assert ohm_file["status"] == "draft" and ohm_file["reviewer"] is None
    assert ov.load(copy_of_overlays / "hookes_amali.json").reviewed


def test_a_reviewed_plan_is_left_out_of_the_next_sheet(copy_of_overlays: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = json.loads((copy_of_overlays / "ohm_explorer.json").read_text(encoding="utf-8"))
    raw.update(status="reviewed", reviewer="R", reviewed_on="2026-11-03")
    (copy_of_overlays / "ohm_explorer.json").write_text(json.dumps(raw), encoding="utf-8")
    original = tools.all_plans
    monkeypatch.setattr(tools, "all_plans", lambda: [(p, plan) for p, plan in original() if plan.id in {"hookes_amali", "ohm_explorer"}])
    out = tmp_path / "review.csv"
    tools.sheet(out)
    assert {r["plan"] for r in csv.DictReader(out.open(encoding="utf-8", newline="")) if not r["plan"].startswith("_")} == {"hookes_amali"}


def test_the_sheet_also_lists_the_pages_words_and_the_kits_words_and_a_web_approval_is_per_string(
    copy_of_overlays: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    web_copy = tools.WEB_STRINGS
    original = tools.all_plans
    monkeypatch.setattr(tools, "all_plans", lambda: [(p, plan) for p, plan in original() if plan.id in {"hookes_amali"}])
    out = tmp_path / "review.csv"
    tools.sheet(out)
    rows = list(csv.DictReader(out.open(encoding="utf-8", newline="")))
    plans = {r["plan"] for r in rows}
    assert {"_web", "_kit", "hookes_amali"} <= plans
    assert any(r["plan"] == "_kit" and r["place"] == "massName#alt" for r in rows)  # the other branch of a yes/no word is on the sheet too
    for r in rows:
        r["approved"] = "yes" if (r["plan"] == "_web" and r["place"] in {"present", "share"}) else ""
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["plan", "place", "english", "malay", "approved"])
        w.writeheader()
        w.writerows(r for r in rows if r["plan"] != "hookes_amali")
    tools.import_sheet(out, "Cikgu Aminah", "2026-11-03")
    web = json.loads(web_copy.read_text(encoding="utf-8"))
    assert web["present"]["reviewed"] is True and web["share"]["reviewed"] is True
    assert web["open"]["reviewed"] is False  # approved one string at a time
    assert not kitwords_reviewed()


def kitwords_reviewed() -> bool:
    from api.i18n import kitwords

    return kitwords.reviewed()
