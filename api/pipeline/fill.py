"""Layer 7: slot fills with contracts. A `custom` slot is the only place a model writes page code, and what it may write is small and typed.

A fill is a few lines of JavaScript that run inside the assembled page, after the Plan's variables exist. The contract names which Kit calls it
may use, how long it may be and which names it may refer to. This is early, named feedback for the model (FILL-* codes); it is NOT the security
boundary. The verifier (scan, render, provenance, reference) still judges the finished page.

Provenance: new in v4. The identifier check is a deliberately simple tokenizer; it errs toward refusing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from api.verify import scan

JS_WORDS = frozenset(
    "var let const function return if else for while do break continue true false null undefined new typeof of in this Math Number String Boolean Array Object".split()
)
SAFE_GLOBALS_ACCESS = frozenset({"Math", "Number", "String", "Boolean", "Array", "Object"})
_STRING = re.compile(r"""("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)""")
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_IDENT = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)")
_SYNAPSE_CALL = re.compile(r"\bSynapse\s*\.\s*([A-Za-z_$][\w$]*)")


@dataclass(frozen=True)
class SlotContract:
    name: str
    allowed_calls: frozenset[str]
    """Kit component names the fill may call, e.g. `text`, `readout`, `constant`."""
    max_lines: int = 10
    max_chars: int = 800


@dataclass(frozen=True)
class FillIssue:
    code: str
    message: str
    hint: str


DEFAULT_CALLS = frozenset({"text", "constant", "readout", "convert", "table", "graph"})


def contract_for(name: str) -> SlotContract:
    return SlotContract(name=name, allowed_calls=DEFAULT_CALLS)


def _strip(code: str) -> str:
    return _STRING.sub('""', _COMMENT.sub("", code))


def _declared(stripped: str) -> set[str]:
    names = set(re.findall(r"\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)", stripped))
    for m in re.finditer(r"\bfunction\s*([A-Za-z_$][\w$]*)?\s*\(([^)]*)\)", stripped):
        if m.group(1):
            names.add(m.group(1))
        names |= set(re.findall(r"[A-Za-z_$][\w$]*", m.group(2)))
    for m in re.finditer(r"\(([^()]*)\)\s*=>", stripped):
        names |= set(re.findall(r"[A-Za-z_$][\w$]*", m.group(1)))
    names |= set(re.findall(r"([A-Za-z_$][\w$]*)\s*=>", stripped))
    return names


def check_fill(code: str, contract: SlotContract, scope: tuple[str, ...]) -> list[FillIssue]:
    issues: list[FillIssue] = []
    if not code.strip():
        return [
            FillIssue(
                "FILL-005",
                "The fill is empty.",
                "Write the few lines the slot needs, or leave the slot out of the plan.",
            )
        ]
    if len(code) > contract.max_chars or len(code.strip().splitlines()) > contract.max_lines:
        issues.append(
            FillIssue(
                "FILL-001",
                f"The fill is longer than {contract.max_lines} lines or {contract.max_chars} characters.",
                f"Keep slot '{contract.name}' under {contract.max_lines} lines.",
            )
        )
    if "</" in code or "<!--" in code or "<script" in code.lower():
        issues.append(FillIssue("FILL-006", "The fill contains markup.", "Write JavaScript only, no tags."))
    hit = scan.forbidden_api_scan(f"<script>{code}</script>")
    if hit is not None:
        issues.append(
            FillIssue(
                "FILL-002",
                f"The fill uses something the page may not use ({hit.reason}).",
                "Use only Kit calls; no network, storage, timers that navigate, eval or DOM injection.",
            )
        )
    stripped = _strip(code)
    if (
        stripped.count("(") != stripped.count(")")
        or stripped.count("{") != stripped.count("}")
        or stripped.count("[") != stripped.count("]")
    ):
        issues.append(FillIssue("FILL-005", "The brackets in the fill do not balance.", "Close every bracket."))
    for call in sorted({m.group(1) for m in _SYNAPSE_CALL.finditer(stripped)}):
        if call not in contract.allowed_calls:
            issues.append(
                FillIssue(
                    "FILL-003",
                    f"The fill calls Synapse.{call}, which slot '{contract.name}' does not allow.",
                    f"Use only: {', '.join(sorted(contract.allowed_calls))}.",
                )
            )
    if (
        re.search(r"\bSynapse\s*(?!\s*\.)", stripped.replace("Synapse.", "Synapse .").replace("Synapse .", "Synapse."))
        and "Synapse[" in stripped
    ):
        issues.append(
            FillIssue(
                "FILL-003", "The fill reaches into Synapse by name lookup.", "Call Synapse.<component>(...) directly."
            )
        )
    known = set(scope) | _declared(stripped) | JS_WORDS | {"Synapse"}
    known_keys = set(re.findall(r"([A-Za-z_$][\w$]*)\s*:", stripped))
    for name in sorted({m.group(1) for m in _IDENT.finditer(stripped)}):
        if name not in known and name not in known_keys:
            issues.append(
                FillIssue(
                    "FILL-004",
                    f"The fill uses '{name}', which is not defined in the page.",
                    f"Use only these names: {', '.join(scope)}.",
                )
            )
    return issues
