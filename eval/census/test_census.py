"""The census table is valid, and the validator actually rejects what it claims to reject."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval.census import census

REPO = Path(__file__).resolve().parents[2]


def test_the_committed_table_passes_check() -> None:
    assert census.problems() == []


def test_the_cli_check_exits_zero() -> None:
    done = subprocess.run(
        [sys.executable, "eval/census/census.py", "--check"], cwd=REPO, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_taxonomy_has_53_topics_with_provenance_and_no_textbook_text() -> None:
    data = json.loads((REPO / "data" / "kssm_topics.json").read_text(encoding="utf-8"))
    assert len(data["topics"]) == 53
    assert data["provenance"]["source_commit"] == "835a2ce"
    assert {t["subject"] for t in data["topics"]} == {"biology", "chemistry", "physics"}
    assert all(len(t["hint"]) < 200 for t in data["topics"])  # phrasing anchors, not passages
    assert all(t["chapter"] is None or isinstance(t["chapter"], int) for t in data["topics"])


def test_every_count_sums_to_53() -> None:
    rows = census.joined(census.load_topics())
    c = census.counts(rows)
    for key in ("subject and form", "subject", "pattern", "model_kind", "expected_lane", "confidence"):
        assert sum(c[key].values()) == 53, key


def test_the_report_file_is_current() -> None:
    """The report is generated; a hand edit or a stale copy fails here."""
    expected = census.render_report(census.joined(census.load_topics()))
    assert (REPO / "refdocs" / "evidence" / "2026-10-16-p0-census.md").read_text(encoding="utf-8") == expected


def test_the_report_states_the_criteria_before_the_table_and_says_estimate() -> None:
    text = census.render_report(census.joined(census.load_topics()))
    assert text.index("## 1. Criteria") < text.index("## 2. The table")
    assert "estimates, not measurements" in text.lower()


def _with(slug: str, index: int, value) -> dict:
    row = list(census.ROWS[slug])
    row[index] = value
    return {**census.ROWS, slug: tuple(row)}


@pytest.mark.parametrize(
    ("index", "value", "needle"),
    [
        (0, "magic", "pattern 'magic'"),
        (1, "vibes", "model_kind 'vibes'"),
        (2, ("ui", "hologram"), "not in the vocabulary"),
        (4, "improvise", "expected_lane 'improvise'"),
        (5, "certain", "confidence 'certain'"),
        (6, "too short", "one line of 25 to 220"),
        (6, "x" * 300, "one line of 25 to 220"),
        (6, "A rationale with an em dash — in it, long enough.", "em or en dash"),
        (6, "A rationale\nwith a line break in the middle of it.", "one line of 25 to 220"),
    ],
)
def test_the_validator_rejects_a_bad_cell(index: int, value, needle: str) -> None:
    found = census.problems(_with("heat", index, value))
    assert any(needle in p for p in found), found


def test_the_validator_rejects_science_without_a_candidate_model_and_the_reverse() -> None:
    assert any("names no candidate model" in p for p in census.problems(_with("heat", 3, ())))
    assert any("does not list `science`" in p for p in census.problems(_with("digestion", 3, ("bio.x",))))


def test_the_validator_rejects_a_missing_extra_or_duplicated_row() -> None:
    missing = {k: v for k, v in census.ROWS.items() if k != "heat"}
    assert any("heat: not annotated" in p for p in census.problems(missing))
    extra = {**census.ROWS, "not_a_topic": census.ROWS["heat"]}
    assert any("not_a_topic: annotated but not in the taxonomy" in p for p in census.problems(extra))
    topics = census.load_topics()
    assert any("duplicate slugs" in p for p in census.problems(census.ROWS, topics + [topics[0]]))
    assert any("expected 53" in p for p in census.problems(census.ROWS, topics[:-1]))


def test_the_ordering_is_by_topics_served_then_name() -> None:
    order = census.model_ordering(census.joined(census.load_topics()))
    counts = [len(slugs) for _, slugs in order]
    assert counts == sorted(counts, reverse=True)
    assert order[0][0] == "gas.boyle"  # the only model that serves two topics
