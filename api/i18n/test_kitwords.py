"""The Kit's Malay words and their review (W12, D-62)."""

from __future__ import annotations

import json
from pathlib import Path

from api.i18n import kitwords


def test_the_kit_words_are_read_from_the_typescript_with_both_branches_of_a_yes_no_word() -> None:
    table = kitwords.words()
    assert table["tryThis"] == {"en": "Try this:", "ms": "Cuba ini:"}
    assert table["massName"]["alt"]["ms"].endswith("di dalam dulang. Tekan Enter untuk menggerakkannya.")
    assert len(table) > 60 and all(v["ms"] and v["en"] for v in table.values())


def test_the_review_is_tied_to_the_exact_words(tmp_path: Path) -> None:
    record = tmp_path / "_kit.json"
    table = kitwords.words()
    record.write_text(json.dumps({"digest": kitwords.digest(table), "reviewer": "Cikgu Aminah", "reviewed_on": "2026-11-03"}), encoding="utf-8")
    assert kitwords.reviewed(record, table)
    changed = {**table, "tryThis": {"en": "Try this:", "ms": "Cuba:"}}
    assert not kitwords.reviewed(record, changed)  # one word changed: the review no longer holds
    record.write_text(json.dumps({"digest": kitwords.digest(table), "reviewer": None, "reviewed_on": None}), encoding="utf-8")
    assert not kitwords.reviewed(record, table)
    assert not kitwords.reviewed(tmp_path / "missing.json", table)


def test_nothing_is_reviewed_until_a_person_reviews_it() -> None:
    assert not kitwords.reviewed()


def test_a_translation_whose_plan_is_reviewed_stays_a_draft_while_the_kit_words_are_not(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    from api.i18n import overlay as ov
    from api.pipeline import library

    seen: dict = {}

    class Store:
        def link_translation(self, of: str, env: str, **kw) -> None:  # noqa: ANN003
            seen.update(kw)

    class Env:
        env_id = "x-1"

    monkeypatch.setattr(library, "build_environment", lambda *a, **k: (Env(), {}))
    monkeypatch.setattr(Store, "put_verified", lambda self, env: None, raising=False)
    raw = json.loads((ov.OVERLAYS / "hookes_amali.json").read_text(encoding="utf-8"))
    raw.update(status="reviewed", reviewer="Cikgu Aminah", reviewed_on="2026-11-03")
    (tmp_path / "hookes_amali.json").write_text(json.dumps(raw), encoding="utf-8")
    from api.pipeline import plan as plan_module

    plan = plan_module.parse((ov.OVERLAYS.parents[2] / "data" / "plans" / "physics-f5-hookes_amali.json").read_text(encoding="utf-8"))
    library.translate(Store(), plan, Env(), None, version="0.1.0", book=None, evidence=None, public_origin="http://x", kit_dist=tmp_path, interaction_seconds=1.0, directory=tmp_path)  # type: ignore[arg-type]
    assert seen["status"] == "draft" and seen["reviewer"] is None
    monkeypatch.setattr(library.kitwords, "reviewed", lambda *a, **k: True)
    library.translate(Store(), plan, Env(), None, version="0.1.0", book=None, evidence=None, public_origin="http://x", kit_dist=tmp_path, interaction_seconds=1.0, directory=tmp_path)  # type: ignore[arg-type]
    assert seen["status"] == "reviewed" and seen["reviewer"] == "Cikgu Aminah"
