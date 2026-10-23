"""Score a wording judge on the fixed L4 case set (D-41). Offline by default: the judge here is a stub, so the numbers measure the PLUMBING and the scorer, not
how well any model reads science.

    uv run python eval/l4/run.py                 # the always-ok stub: detection 0, which is the floor any real judge must beat
    uv run python eval/l4/run.py --judge oracle  # the answer key itself: detection 100 percent, which proves the scorer

A real model is measured in W8 through the paid-run script, with a projected amount, the cost-auditor and the owner's typed go (rule 7). This file refuses
`--live` rather than spend money.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.pipeline.plan import Plan  # noqa: E402
from eval.l4.cases import Case, apply, load_cases, plan_of  # noqa: E402

Judge = Callable[[Case, Plan], bool]
"""Returns True when the judge accepts the Plan's words."""


@dataclass(frozen=True)
class Score:
    planted: int
    caught: int
    controls: int
    wrongly_refused: int
    by_kind: dict[str, tuple[int, int]]
    """kind -> (planted, caught)"""

    @property
    def detection(self) -> float:
        return self.caught / self.planted if self.planted else 0.0

    @property
    def false_alarm(self) -> float:
        return self.wrongly_refused / self.controls if self.controls else 0.0


def score(cases: list[Case], judge: Judge) -> Score:
    planted = caught = controls = wrong = 0
    kinds: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for case in cases:
        accepted = judge(case, apply(case, plan_of(case)))
        if case.expect == "refuse":
            planted += 1
            kinds[case.kind][0] += 1
            if not accepted:
                caught += 1
                kinds[case.kind][1] += 1
        else:
            controls += 1
            if not accepted:
                wrong += 1
    return Score(planted, caught, controls, wrong, {k: (v[0], v[1]) for k, v in sorted(kinds.items())})


def always_ok(_case: Case, _plan: Plan) -> bool:
    return True


def oracle(case: Case, _plan: Plan) -> bool:
    return case.expect == "accept"


def report(name: str, s: Score) -> str:
    lines = [
        f"judge: {name}",
        f"planted defects caught: {s.caught} of {s.planted} ({s.detection:.0%})",
        f"true controls wrongly refused: {s.wrongly_refused} of {s.controls} ({s.false_alarm:.0%})",
    ]
    lines += [f"  {kind}: {caught} of {planted}" for kind, (planted, caught) in s.by_kind.items()]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--judge", choices=("always-ok", "oracle"), default="always-ok")
    parser.add_argument("--live", action="store_true", help="not available here: a real model is measured in W8 with the owner's go")
    args = parser.parse_args()
    if args.live:
        print("Refused: a paid measurement needs a projected amount, the cost-auditor and the owner's typed go (CLAUDE.md rule 7). It is workstream W8.")
        return 2
    judge = {"always-ok": always_ok, "oracle": oracle}[args.judge]
    print(report(args.judge, score(load_cases(), judge)))
    print("A stub measures the plumbing and the scorer only. It says nothing about how well a model reads science.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
