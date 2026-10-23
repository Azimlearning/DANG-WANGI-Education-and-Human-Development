"""The L4 case set: planted wording defects and true controls, built deterministically from the 16 golden Plans (D-41, hard constraint 9).

Why it exists. L4 is a model reading words, so its detection rate cannot be assumed, and it must not be mixed into the L6 rate (L6 is the model-free verifier;
a stub judge there would raise that number without any real model being measured). This set is fixed BEFORE any paid run: the file `data/l4/cases.json` and
its hash `data/l4/cases.sha256` are pinned by a test, and a change to either is a declared amendment, not an edit.

What a case is. A "false" case is a golden Plan with ONE change that makes a sentence untrue (a direction word flipped: "increases" to "decreases",
"proportional" to "inversely proportional") or a control's unit swapped for a wrong one. A "true" case is the Plan as written. The answer key comes from the
construction, not from a person: a flipped direction word almost always makes a sentence false, but a few flips may land on a sentence that is still
acceptable, and a person has not reviewed the key (W11). Read a measured detection rate with that in mind.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from api.pipeline.plan import Plan, parse

REPO = Path(__file__).resolve().parents[2]
PLANS = REPO / "data" / "plans"
CASES_PATH = REPO / "data" / "l4" / "cases.json"
HASH_PATH = REPO / "data" / "l4" / "cases.sha256"
MAX_FLIPS_PER_PLAN = 2

# (pattern, replacement, kind). The first rule that matches a sentence is the one applied. Whole words, case preserved on the first letter.
FLIPS: list[tuple[str, str, str]] = [
    (r"\binversely proportional\b", "directly proportional", "relation flipped"),
    (r"\bdirectly proportional\b", "inversely proportional", "relation flipped"),
    (r"(?<!inversely )(?<!directly )\bproportional\b", "inversely proportional", "relation flipped"),
    (r"\bincreases\b", "decreases", "direction flipped"),
    (r"\bdecreases\b", "increases", "direction flipped"),
    (r"\brises\b", "falls", "direction flipped"),
    (r"\bfalls\b", "rises", "direction flipped"),
    (r"\bdoubles\b", "halves", "size flipped"),
    (r"\bhalves\b", "doubles", "size flipped"),
    (r"\bgreater\b", "smaller", "size flipped"),
    (r"\bsmaller\b", "greater", "size flipped"),
    (r"\bhigher\b", "lower", "size flipped"),
    (r"\blower\b", "higher", "size flipped"),
    (r"\bmore\b", "less", "size flipped"),
    (r"\bless\b", "more", "size flipped"),
    (r"\bfaster\b", "slower", "size flipped"),
    (r"\bslower\b", "faster", "size flipped"),
]
WRONG_UNIT = {"N": "kg", "kg": "N", "m": "s", "s": "m", "V": "A", "A": "V", "Pa": "N", "J": "W", "W": "J", "mol": "g", "g": "mol", "cm3": "g", "dm3": "g"}


@dataclass(frozen=True)
class Case:
    id: str
    plan: str
    """The golden Plan's file name under data/plans."""
    expect: str
    """`refuse` for a planted defect, `accept` for the unchanged Plan."""
    kind: str
    field: str
    """Dotted path of the changed field, for example `sentences.1` or `controls.0.unit`; empty for an unchanged Plan."""
    original: str
    mutated: str


def _swap(text: str) -> tuple[str, str] | None:
    for pattern, replacement, kind in FLIPS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            word = match.group(0)
            new = replacement[0].upper() + replacement[1:] if word[0].isupper() else replacement
            return text[: match.start()] + new + text[match.end() :], kind
    return None


def _prose_fields(plan: Plan) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = [("note", plan.note)]
    out += [(f"sentences.{i}", s) for i, s in enumerate(plan.sentences)]
    out += [(f"hints.{i}", s) for i, s in enumerate(plan.hints)]
    out += [(f"worked_solution.{i}", s) for i, s in enumerate(plan.worked_solution)]
    if plan.predict is not None:
        out.append(("predict.reveal", plan.predict.reveal))
    if plan.concept_check is not None:
        out.append(("concept_check.explanation", plan.concept_check.explanation))
    if plan.experiment is not None:
        out.append(("experiment.hypothesis", plan.experiment.hypothesis))
    return out


def build_cases() -> list[Case]:
    cases: list[Case] = []
    for path in sorted(PLANS.glob("*.json")):
        plan = parse(path.read_text(encoding="utf-8"))
        stem = path.stem
        cases.append(Case(f"{stem}:true", path.name, "accept", "unchanged", "", "", ""))
        flips = 0
        for field, text in _prose_fields(plan):
            if flips >= MAX_FLIPS_PER_PLAN:
                break
            swapped = _swap(text)
            if swapped is not None:
                cases.append(Case(f"{stem}:{field}", path.name, "refuse", swapped[1], field, text, swapped[0]))
                flips += 1
        unit = plan.controls[0].unit
        if unit in WRONG_UNIT:
            cases.append(Case(f"{stem}:controls.0.unit", path.name, "refuse", "wrong unit", "controls.0.unit", unit, WRONG_UNIT[unit]))
    return cases


def apply(case: Case, plan: Plan) -> Plan:
    """The Plan a judge is shown for this case: unchanged for a true case, with exactly one field changed for a planted defect."""
    if case.expect == "accept":
        return plan
    data = plan.model_dump()
    *parents, last = case.field.split(".")
    node: Any = data
    for part in parents:
        node = node[int(part)] if isinstance(node, list) else node[part]
    if isinstance(node, list):
        node[int(last)] = case.mutated
    else:
        node[last] = case.mutated
    return Plan.model_validate(data)


def plan_of(case: Case) -> Plan:
    return parse((PLANS / case.plan).read_text(encoding="utf-8"))


def serialise(cases: list[Case]) -> str:
    return json.dumps([asdict(c) for c in cases], indent=2, ensure_ascii=False) + "\n"


def load_cases() -> list[Case]:
    return [Case(**row) for row in json.loads(CASES_PATH.read_text(encoding="utf-8"))]


def file_sha256() -> str:
    """Hash of the case file with line endings normalised to LF: git may check the file out with CRLF (core.autocrlf on Windows), and the pinned hash must
    not depend on that."""
    return hashlib.sha256(CASES_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


if __name__ == "__main__":  # regenerate the committed set (a declared amendment: also update the pinned hash and say why in the changelog)
    built = build_cases()
    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASES_PATH.write_text(serialise(built), encoding="utf-8", newline="\n")
    HASH_PATH.write_text(file_sha256() + "\n", encoding="utf-8", newline="\n")
    refuse = sum(c.expect == "refuse" for c in built)
    print(f"wrote {len(built)} cases ({refuse} planted defects, {len(built) - refuse} true controls) and {HASH_PATH.name}")
