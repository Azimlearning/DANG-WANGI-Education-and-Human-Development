"""The L4 case set is fixed before any paid run (hard constraint 9): these tests pin it, check how it was built, and prove the scorer."""

from __future__ import annotations

import pytest

from api.pipeline import prompts
from api.pipeline.plan import Plan
from eval.l4 import cases as c
from eval.l4.run import Score, always_ok, main, oracle, score


def test_the_committed_set_is_the_set_the_generator_builds() -> None:
    assert c.serialise(c.build_cases()) == c.CASES_PATH.read_text(encoding="utf-8").replace("\r\n", "\n"), (
        "data/l4/cases.json differs from what eval/l4/cases.py builds: either the golden Plans changed or the rules did. "
        "Regenerating is a declared amendment (python -m eval.l4.cases), recorded in the changelog."
    )


def test_the_set_is_pinned_by_its_hash() -> None:
    pinned = c.HASH_PATH.read_text(encoding="utf-8").strip()
    assert pinned == c.file_sha256(), "data/l4/cases.json changed without a declared amendment (update data/l4/cases.sha256 and say why)"


def test_the_set_is_big_enough_and_has_both_sides() -> None:
    cases = c.load_cases()
    planted = [x for x in cases if x.expect == "refuse"]
    controls = [x for x in cases if x.expect == "accept"]
    assert len(controls) == 17 and len(planted) >= 20
    assert {"relation flipped", "direction flipped", "size flipped", "wrong unit"} <= {x.kind for x in planted}
    assert len({x.id for x in cases}) == len(cases)


@pytest.mark.parametrize("case", [x for x in c.load_cases() if x.expect == "refuse"], ids=lambda x: x.id)
def test_a_planted_case_changes_exactly_one_field_and_stays_a_valid_plan(case: c.Case) -> None:
    original = c.plan_of(case)
    changed = c.apply(case, original)
    assert isinstance(changed, Plan) and changed != original
    before, after = original.model_dump(), changed.model_dump()

    def leaves(node: object, path: str = "") -> dict[str, object]:
        if isinstance(node, dict):
            return {k: v for key, value in node.items() for k, v in leaves(value, f"{path}.{key}" if path else key).items()}
        if isinstance(node, list):
            return {k: v for i, value in enumerate(node) for k, v in leaves(value, f"{path}.{i}" if path else str(i)).items()}
        return {path: node}

    b, a = leaves(before), leaves(after)
    different = [p for p in b if b[p] != a.get(p)]
    assert different == [case.field] and a[case.field] == case.mutated and b[case.field] == case.original


def test_a_true_case_is_the_plan_exactly_as_written() -> None:
    for case in (x for x in c.load_cases() if x.expect == "accept"):
        plan = c.plan_of(case)
        assert c.apply(case, plan) is plan


def test_every_case_makes_a_judge_request_inside_the_token_cap() -> None:
    for case in c.load_cases():
        request = prompts.wording_request(c.apply(case, c.plan_of(case)))
        assert request.purpose == "wording"
        if case.expect == "refuse" and case.field != "controls.0.unit":
            assert case.mutated[:30] in request.prompt


def test_the_scorer_gives_the_always_ok_stub_zero_and_the_answer_key_everything() -> None:
    cases = c.load_cases()
    floor, ceiling = score(cases, always_ok), score(cases, oracle)
    assert floor.caught == 0 and floor.detection == 0.0 and floor.wrongly_refused == 0
    assert ceiling.caught == ceiling.planted and ceiling.wrongly_refused == 0 and ceiling.detection == 1.0
    assert sum(p for p, _ in ceiling.by_kind.values()) == ceiling.planted


def test_the_scorer_counts_a_false_alarm_on_a_true_control() -> None:
    cases = c.load_cases()
    got = score(cases, lambda _c, _p: False)  # a judge that refuses everything
    assert got.caught == got.planted and got.wrongly_refused == got.controls and got.false_alarm == 1.0


def test_the_score_arithmetic_handles_an_empty_side() -> None:
    assert Score(0, 0, 0, 0, {}).detection == 0.0 and Score(0, 0, 0, 0, {}).false_alarm == 0.0


def test_the_runner_refuses_to_spend(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["run.py", "--live"])
    assert main() == 2
    assert "owner's typed go" in capsys.readouterr().out
