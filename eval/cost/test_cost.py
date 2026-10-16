from __future__ import annotations

from eval.cost.project import REPORT, build


def test_the_cost_projection_is_up_to_date_and_states_it_waits_for_the_owner() -> None:
    text = build()
    assert REPORT.read_text(encoding="utf-8") == text, "run: uv run python eval/cost/project.py"
    assert (
        "No model call was made" in text and "Nothing is sent until the owner replies" in text and "Assumptions" in text
    )


def test_the_high_case_is_not_below_the_low_case() -> None:
    text = build()
    low = float(text.split("| Low | **")[1].split("**")[0])
    high = float(text.split("| High | **")[1].split("**")[0])
    pess = float(text.split("| Pessimistic | **")[1].split("**")[0])
    bound = float(text.split("| Hard bound | **")[1].split("**")[0])
    assert 0 < low < high < pess < bound
