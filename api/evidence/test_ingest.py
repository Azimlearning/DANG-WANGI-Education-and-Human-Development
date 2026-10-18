"""The ingestion script's logic on synthetic input: document ids, the guesses it makes from a path, resuming, and that the manifest holds no text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.evidence import ingest
from api.evidence.corpus import Corpus


@pytest.mark.parametrize(
    ("path", "doc_id"),
    [
        ("Textbook/Biology/Form 4/[DLP] BIOLOGY F4.pdf", "textbook-biology-form-4-dlp-biology-f4"),
        ("Experiment/CHEM/Experiments/Aktiviti _ Eksperimen Kimia.pdf", "experiment-chem-experiments-aktiviti-eksperimen-kimia"),
        ("Experiment/CHEM/00 SHORTLISTED EXPERIMENT/Aktiviti _ Eksperimen Kimia.pdf", "experiment-chem-00-shortlisted-experiment-aktiviti-eksperimen-kimia"),
    ],
)
def test_the_document_id_is_a_slug_of_the_whole_path_so_same_named_files_do_not_collide(path: str, doc_id: str) -> None:
    assert ingest.slug(Path(path)) == doc_id


@pytest.mark.parametrize(
    ("path", "subject", "form", "language", "kind"),
    [
        ("Textbook/Biology/Form 4/[DLP] BIOLOGY F4.pdf", "biology", 4, "en", "textbook"),
        ("Textbook/Biology/Form 5/[MALAY] BIOLOGI TING 5.pdf", "biology", 5, "ms", "textbook"),
        ("Textbook/Chemistry/T4 BT KIM PART 2 - KIMIA.pdf", "chemistry", 4, "ms", "textbook"),
        ("Textbook/Physics/PHYSICS F5_removed.pdf", "physics", 5, "en", "textbook"),
        ("Experiment/PHYSIC/00_Physics_Form_4_Combined.pdf", "physics", 4, "en", "experiment"),
        ("Experiment/BIOLOGY/Shortlisted/5.1 Effect of temperature on amylase activity.pdf", "biology", None, "en", "experiment"),
    ],
)
def test_the_guesses_from_a_path_cover_the_shapes_of_the_real_folder(
    path: str, subject: str, form: int | None, language: str, kind: str
) -> None:
    got = ingest.describe(Path(path))
    assert (got["subject"], got["form"], got["language"], got["kind"]) == (subject, form, language, kind)


def test_a_run_writes_one_jsonl_per_pdf_and_a_manifest_with_no_text_and_a_rerun_skips_unchanged_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, out = tmp_path / "pdfs", tmp_path / "corpus"
    (source / "Textbook" / "Physics").mkdir(parents=True)
    (source / "Textbook" / "Physics" / "PHYSICS F5.pdf").write_bytes(b"%PDF-1.4 synthetic one")
    (source / "Experiment").mkdir()
    (source / "Experiment" / "PHYSICS F5.pdf").write_bytes(b"%PDF-1.4 synthetic two")
    calls: list[str] = []

    def fake_extract(pdf: Path) -> tuple[list[dict], int]:
        calls.append(pdf.parent.name)
        return [{"page": 1, "text": "A spring obeys a law when it is stretched."}, {"page": 2, "text": "3"}], 0

    monkeypatch.setattr(ingest, "extract", fake_extract)
    assert ingest.main(["--pdf-dir", str(source), "--out", str(out)]) == 0
    assert sorted(p.name for p in out.glob("*.jsonl")) == ["experiment-physics-f5.jsonl", "textbook-physics-physics-f5.jsonl"]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert [d["pages"] for d in manifest["documents"]] == [2, 2] and all(d["empty_pages"] == 1 for d in manifest["documents"])
    assert "spring" not in (out / "manifest.json").read_text(encoding="utf-8")  # the manifest never carries text
    assert Corpus.load(out).page_count("textbook-physics-physics-f5") == 2  # and the folder loads as a corpus
    calls.clear()
    ingest.main(["--pdf-dir", str(source), "--out", str(out)])
    assert calls == []  # unchanged hashes: nothing is read again
    ingest.main(["--pdf-dir", str(source), "--out", str(out), "--force"])
    assert len(calls) == 2


def test_two_pdfs_that_would_share_an_id_are_refused(tmp_path: Path) -> None:
    (tmp_path / "a b").mkdir()
    (tmp_path / "a-b").mkdir()
    (tmp_path / "a b" / "x.pdf").write_bytes(b"%PDF one")
    (tmp_path / "a-b" / "x.pdf").write_bytes(b"%PDF two")
    with pytest.raises(SystemExit, match="same document id"):
        ingest.main(["--pdf-dir", str(tmp_path), "--out", str(tmp_path / "out")])
