"""The leak check finds a copied run of a quotation and ignores common phrasing, on synthetic text."""

from __future__ import annotations

from pathlib import Path

from eval.evidence.leak_check import leaks

QUOTE = "Invented passage: a brass lever turns slowly whenever the dial beside it is rotated past its marked stop."


def test_a_nine_word_run_of_a_quotation_in_a_file_is_a_leak(tmp_path: Path) -> None:
    copied = tmp_path / "notes.md"
    copied.write_text("Remember: a brass lever turns slowly whenever the dial beside it is rotated.", encoding="utf-8")
    assert [cid for _, cid in leaks({"q": QUOTE}, [copied])] == ["q"]


def test_case_and_spacing_do_not_hide_a_leak(tmp_path: Path) -> None:
    copied = tmp_path / "x.py"
    copied.write_text("A  BRASS lever\nturns slowly whenever   the dial beside it is rotated", encoding="utf-8")
    assert leaks({"q": QUOTE}, [copied])


def test_a_short_shared_phrase_is_not_a_leak(tmp_path: Path) -> None:
    common = tmp_path / "doc.md"
    common.write_text("A brass lever turns slowly. The dial beside it is a different thing.", encoding="utf-8")
    assert leaks({"q": QUOTE}, [common]) == []


def test_binary_files_are_skipped(tmp_path: Path) -> None:
    blob = tmp_path / "a.bin"
    blob.write_bytes(b"\xff\xfe\x00 not text")
    assert leaks({"q": QUOTE}, [blob]) == []
