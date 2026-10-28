"""The overlay checks (W12, D-62): a translation that changes a number, drops or adds a sentence, or is still English is refused before anything is built."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from api.i18n import overlay as ov
from api.pipeline import plan as plan_module

PLANS = Path(__file__).resolve().parents[2] / "data" / "plans"


def hooke() -> plan_module.Plan:
    return plan_module.parse((PLANS / "physics-f5-hookes_amali.json").read_text(encoding="utf-8"))


def overlay_of(plan: plan_module.Plan, **over) -> ov.Overlay:  # noqa: ANN003
    raw = json.loads((ov.OVERLAYS / f"{plan.id}.json").read_text(encoding="utf-8"))
    raw.update(over)
    return ov.Overlay(plan=raw["plan"], lang="ms", status=raw["status"], reviewer=raw["reviewer"], reviewed_on=raw["reviewed_on"], strings=raw["strings"])


def test_every_plan_has_a_complete_overlay_that_applies() -> None:
    for path in sorted(PLANS.glob("*.json")):
        plan = plan_module.parse(path.read_text(encoding="utf-8"))
        overlay = ov.load_for(plan.id)
        assert overlay is not None, f"{plan.id} has no Bahasa Melayu overlay"
        assert ov.problems(plan, overlay) == [], plan.id
        malay = ov.apply(plan, overlay)
        # Nothing but words changed: ids, units, numbers, models and ranges are the English Plan's.
        assert [c.id for c in malay.controls] == [c.id for c in plan.controls]
        assert [(c.min, c.max, c.value, c.grid, c.unit) for c in malay.controls] == [(c.min, c.max, c.value, c.grid, c.unit) for c in plan.controls]
        assert [m.model_dump() for m in malay.models] == [m.model_dump() for m in plan.models]
        assert [(r.unit, r.digits, r.source) for r in malay.readouts] == [(r.unit, r.digits, r.source) for r in plan.readouts]
        assert malay.citation_ids == plan.citation_ids
        assert malay.topic == plan.topic
        assert malay.title != plan.title


def test_the_translatable_places_are_every_word_a_student_reads() -> None:
    places = ov.translatable(hooke())
    for pointer in ("/title", "/note", "/controls/0/label", "/readouts/0/label", "/steps/0", "/hints/0", "/predict/prompt", "/concept_check/explanation", "/experiment/aim"):
        assert pointer in places
    assert not any(p.endswith("/unit") or p.endswith("/id") for p in places)


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        (lambda s: s.pop("/steps/0"), "missing /steps/0"),
        (lambda s: s.update({"/steps/9": "Langkah tambahan"}), "extra /steps/9"),
        (lambda s: s.update({"/sentences/0": "Pemalar spring ialah 51 N/m."}), "digits differ"),
        (lambda s: s.update({"/sentences/0": "Pemalar spring ialah N/m."}), "digits differ"),
        (lambda s: s.update({"/title": ""}), "is empty"),
        (lambda s: s.update({"/hints/2": "Add one mass at a time and record the extension each time."}), "still English"),
    ],
)
def test_a_planted_defect_in_an_overlay_is_refused(change, fragment: str) -> None:  # noqa: ANN001
    plan = hooke()
    overlay = overlay_of(plan)
    strings = copy.deepcopy(overlay.strings)
    change(strings)
    bad = ov.Overlay(overlay.plan, overlay.lang, overlay.status, overlay.reviewer, overlay.reviewed_on, strings)
    found = ov.problems(plan, bad)
    assert any(fragment in p for p in found), found
    with pytest.raises(ov.OverlayError):
        ov.apply(plan, bad)


def test_an_overlay_for_another_plan_is_refused() -> None:
    plan = hooke()
    other = overlay_of(plan)
    wrong = ov.Overlay("ohm_explorer", other.lang, other.status, other.reviewer, other.reviewed_on, other.strings)
    assert any("not 'hookes_amali'" in p for p in ov.problems(plan, wrong))


def test_a_malay_sentence_the_plan_cannot_hold_is_refused() -> None:
    plan = hooke()
    overlay = overlay_of(plan)
    strings = dict(overlay.strings)
    strings["/title"] = "Hukum Hooke " * 8  # over the 60 character limit of a title
    long = ov.Overlay(overlay.plan, overlay.lang, overlay.status, overlay.reviewer, overlay.reviewed_on, strings)
    with pytest.raises(ov.OverlayError, match="not valid"):
        ov.apply(plan, long)


def test_a_reviewed_file_must_name_its_reviewer_and_the_date(tmp_path: Path) -> None:
    raw = json.loads((ov.OVERLAYS / "hookes_amali.json").read_text(encoding="utf-8"))
    raw["status"] = "reviewed"
    path = tmp_path / "hookes_amali.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ov.OverlayError, match="reviewer"):
        ov.load(path)
    raw.update(reviewer="Cikgu Aminah", reviewed_on="2026-11-03")
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert ov.load(path).reviewed


def test_a_file_with_unknown_fields_or_another_language_is_refused(tmp_path: Path) -> None:
    raw = json.loads((ov.OVERLAYS / "hookes_amali.json").read_text(encoding="utf-8"))
    path = tmp_path / "x.json"
    path.write_text(json.dumps({**raw, "html": "<p>x</p>"}), encoding="utf-8")
    with pytest.raises(ov.OverlayError, match="fields"):
        ov.load(path)
    path.write_text(json.dumps({**raw, "lang": "fr"}), encoding="utf-8")
    with pytest.raises(ov.OverlayError, match="lang"):
        ov.load(path)
    path.write_text(json.dumps({**raw, "status": "approved"}), encoding="utf-8")
    with pytest.raises(ov.OverlayError, match="status"):
        ov.load(path)


def test_the_assembler_builds_a_malay_page_with_a_malay_document_language() -> None:
    from api import kitmanifest
    from api.kit import latest_version
    from api.pipeline.assemble import assemble
    from api.pipeline.plan_checks import check

    kit = Path(__file__).resolve().parents[2] / "packages" / "kit" / "dist"
    manifest = kitmanifest.load(kit, latest_version(kit))
    plan = hooke()
    malay = ov.apply(plan, overlay_of(plan))
    assert check(malay, manifest, lang="ms") == []
    page = assemble(malay, manifest, lang="ms").html
    assert '<html lang="ms">' in page
    assert 'lang: "ms"' in page
    assert "Makmal fizik interaktif" in page
    english = assemble(plan, manifest).html
    assert '<html lang="en">' in english
    assert "lang:" not in english.split("Synapse.environment(")[1].split("\n")[0]
