"""Layers L1 (provenance) and L3 (numeric cross-check) as pure functions of the Kit's audit data.

The browser reports facts (`Synapse.audit()`); everything that DECIDES lives here, where it can be tested with forged audits and no
browser. An audit is a plain dict. Nothing here trusts it more than the numbers it can recompute: the displayed text is compared with
the Kit's own formatted value, and the value is compared with an independent reference evaluated from the provenance chain.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from api.verify.references import REFERENCES, evaluate_model, unit_factor

GROUNDED_LEAVES = ("control", "constant")
COPY_NUMBER = re.compile(r"(?<![A-Za-z0-9_.])-?\d+(?:\.\d+)?")
# A number is context, not a quantity, after these words ("Step 2", "Form 5") or as a list marker ("1. ").
COPY_CONTEXT = re.compile(
    r"(?:step|stage|part|form|tingkatan|chapter|bab|figure|rajah|table|jadual|question|soalan)\s*$", re.IGNORECASE
)
LIST_MARKER = re.compile(r"(?:^|\n)\s*$")


@dataclass(frozen=True)
class Problem:
    rule: str
    reason: str


# ── provenance chains ───────────────────────────────────────────────────────────────────────────────────────────────────


def chain_problem(chain: dict) -> Problem | None:
    """Why this readout's provenance chain is not acceptable, or None when it is grounded in controls and constants through models."""
    kind = chain.get("kind")
    inputs = chain.get("inputs") or {}
    if kind in GROUNDED_LEAVES:
        return None
    if kind == "free":
        return Problem(
            "ungrounded_readout", "the value comes from an observable that no control or science model produced"
        )
    if kind == "derived":
        return Problem(
            "unaudited_arithmetic",
            "the value depends on arithmetic written in the page; only a unit conversion is allowed",
        )
    if kind == "convert":
        if "x" not in inputs:
            return Problem("ungrounded_readout", "a conversion without a source")
        try:
            want = unit_factor(str(chain.get("from")), str(chain.get("to")))
        except (KeyError, ValueError) as exc:
            return Problem(
                "bad_unit_factor", f"{chain.get('from')} to {chain.get('to')} is not a valid unit change: {exc}"
            )
        if not math.isclose(float(chain.get("factor", 0.0)), want, rel_tol=1e-12):
            return Problem(
                "bad_unit_factor",
                f"the Kit converts {chain.get('from')} to {chain.get('to')} by {chain.get('factor')} but the factor is {want}",
            )
        return chain_problem(inputs["x"])
    if kind == "model":
        model_id = chain.get("id")
        if model_id not in REFERENCES:
            return Problem("unknown_model", f"model '{model_id}' has no independent reference")
        ref = REFERENCES[model_id]
        if set(inputs) != set(ref.inputs):
            return Problem(
                "ungrounded_readout",
                f"model '{model_id}' was given inputs {sorted(inputs)}, expected {sorted(ref.inputs)}",
            )
        for child in inputs.values():
            found = chain_problem(child)
            if found:
                return found
        return None
    return Problem("ungrounded_readout", f"unknown provenance kind {kind!r}")


def evaluate_chain(chain: dict, controls: dict[str, float], constants: dict[str, float]) -> float:
    """The reference value of a grounded chain at the given control values. Raises ValueError/KeyError when it cannot be evaluated."""
    kind = chain["kind"]
    inputs = chain.get("inputs") or {}
    if kind == "control":
        return controls[chain["id"]]
    if kind == "constant":
        return constants[chain["id"]]
    if kind == "convert":
        return chain["factor"] * evaluate_chain(inputs["x"], controls, constants)
    if kind == "model":
        values = {name: evaluate_chain(child, controls, constants) for name, child in inputs.items()}
        return evaluate_model(chain["id"], dict(chain.get("params") or {}), values)
    raise ValueError(f"cannot evaluate a {kind!r} node")


def models_in(chain: dict) -> list[tuple[str, tuple[tuple[str, float], ...]]]:
    """Every science model in a chain as (id, ((param, value), ...)), in a stable order, without repeats."""
    found: list[tuple[str, tuple[tuple[str, float], ...]]] = []
    if chain.get("kind") == "model":
        found.append((chain["id"], tuple(sorted((k, float(v)) for k, v in (chain.get("params") or {}).items()))))
    for child in (chain.get("inputs") or {}).values():
        for m in models_in(child):
            if m not in found:
                found.append(m)
    return found


# ── backed numbers ──────────────────────────────────────────────────────────────────────────────────────────────────────


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def backed_numbers(audit: dict) -> list[float]:
    """Numbers a sentence may state: control ranges, defaults and grid positions, declared constants and model parameters."""
    values: list[float] = []
    for c in audit.get("controls", []):
        values += [c["min"], c["max"], c["default"]]
        values += [c["min"] + (c["max"] - c["min"]) * i / c["grid"] for i in range(c["grid"] + 1)]
    values += [c["value"] for c in audit.get("constants", [])]
    for r in audit.get("readouts", []):
        for _, params in models_in(r["chain"]):
            values += [v for _, v in params]
    return values


def copy_number_problems(audit: dict) -> list[Problem]:
    backed = backed_numbers(audit)
    out: list[Problem] = []
    for entry in audit.get("copy", []):
        text = entry["text"]
        for m in COPY_NUMBER.finditer(text):
            before = text[: m.start()]
            if COPY_CONTEXT.search(before) or LIST_MARKER.search(before):
                continue
            value = float(m.group())
            if not any(_close(value, b) for b in backed):
                out.append(
                    Problem(
                        "unbacked_copy_number",
                        f"the text states {m.group()} which is not a control value, a constant or a model parameter: {text[:80]!r}",
                    )
                )
    return out


def _chain_unit(chain: dict, audit: dict) -> str | None:
    """The unit a grounded chain's value is in, from the independent references and the declared controls and constants; None if unknown."""
    kind = chain.get("kind")
    if kind == "model":
        ref = REFERENCES.get(chain.get("id", ""))
        return ref.output_unit if ref else None
    if kind == "convert":
        return chain.get("to")
    if kind == "control":
        return next((c["unit"] for c in audit.get("controls", []) if c["id"] == chain.get("id")), None)
    if kind == "constant":
        return next((c["unit"] for c in audit.get("constants", []) if c["label"] == chain.get("id")), None)
    return None


# ── L1 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────


def l1_problems(audit: dict | None) -> list[Problem]:
    """Layer L1 on one audit snapshot. Empty means the page's numbers are grounded and unaltered at this moment."""
    if not isinstance(audit, dict):
        return [Problem("kit_missing", "the page did not report a Kit audit (is window.Synapse the Kit?)")]
    out: list[Problem] = []
    if not audit.get("intact"):
        out.append(Problem("kit_not_intact", "window.Synapse is not the sealed Kit object"))
    for r in audit.get("readouts", []):
        found = chain_problem(r["chain"])
        if found:
            out.append(Problem(found.rule, f"readout '{r['label']}': {found.reason}"))
        shown = _chain_unit(r["chain"], audit)
        if found is None and shown is not None and shown != r["unit"]:
            out.append(
                Problem(
                    "wrong_unit",
                    f"readout '{r['label']}' is labelled {r['unit']!r} but its value is in {shown!r}",
                )
            )
        if r["displayed"] != r["expected"]:
            out.append(
                Problem(
                    "readout_mismatch",
                    f"readout '{r['label']}' shows {r['displayed']!r} but its value is {r['expected']!r}",
                )
            )
    for m in audit.get("ownedMismatches", []):
        out.append(
            Problem(
                "owned_changed",
                f"a <{m['tag']}> the Kit made was edited: expected {m['expected']!r}, found {m['actual']!r}",
            )
        )
    for a in audit.get("unownedAttributeNumbers", []):
        out.append(
            Problem(
                "unowned_attribute_number",
                f"{a['attribute']} on <{a['element']}> holds a number the Kit did not set: {a['value']!r}",
            )
        )
    if audit.get("shadowRoots", 0):
        out.append(Problem("shadow_root", "an element has a shadow root; its content cannot be audited"))
    for u in audit.get("unownedNumbers", []):
        out.append(
            Problem("unowned_number", f"a number appears outside the Kit's elements in <{u['parent']}>: {u['text']!r}")
        )
    out += copy_number_problems(audit)
    return out


# ── L3 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

DISPLAY_FLOOR = 1e-12


def l3_problems(audit: dict) -> tuple[list[Problem], int]:
    """Layer L3 on one snapshot: every grounded readout compared with its independent reference. Returns (problems, comparisons made)."""
    problems: list[Problem] = []
    compared = 0
    controls = {c["id"]: float(c["value"]) for c in audit.get("controls", [])}
    constants = {c["label"]: float(c["value"]) for c in audit.get("constants", [])}
    for r in audit.get("readouts", []):
        if chain_problem(r["chain"]) is not None:
            continue  # L1 already refused it; there is no reference to compare with
        try:
            expected = evaluate_chain(r["chain"], controls, constants)
        except (ValueError, KeyError) as exc:
            problems.append(
                Problem(
                    "reference_error",
                    f"readout '{r['label']}': the reference could not be evaluated at {controls}: {exc}",
                )
            )
            continue
        compared += 1
        digits = int(r["digits"])
        match = re.match(r"^\s*(-?\d+(?:\.\d+)?)", r["displayed"])
        if not match:
            problems.append(
                Problem("non_finite_readout", f"readout '{r['label']}' shows {r['displayed']!r}, which is not a number")
            )
            continue
        shown = float(match.group(1))
        half_step = 0.5 * 10 ** (-digits) + DISPLAY_FLOOR
        if abs(shown - expected) > half_step + 1e-9 * abs(expected):
            problems.append(
                Problem(
                    "numeric_mismatch",
                    f"readout '{r['label']}' shows {shown} but the independent reference gives {expected} at {controls}",
                )
            )
        if not math.isclose(float(r["value"]), expected, rel_tol=1e-9, abs_tol=1e-12):
            problems.append(
                Problem(
                    "numeric_mismatch",
                    f"readout '{r['label']}' holds {r['value']} but the independent reference gives {expected} at {controls}",
                )
            )
    return problems, compared


def plan_problems(audit: dict, plan_models: list[dict] | None) -> list[Problem]:
    """The models the page really uses must be exactly the ones the plan declares, with the same parameters."""
    if plan_models is None:
        return []
    used = {m for r in audit.get("readouts", []) for m in models_in(r["chain"])}
    planned = {(m["id"], tuple(sorted((k, float(v)) for k, v in m.get("params", {}).items()))) for m in plan_models}
    missing = sorted(planned - used)
    extra = sorted(used - planned)
    if not missing and not extra:
        return []

    def show(models: list) -> str:
        return "; ".join(f"{model_id} {dict(params)}" for model_id, params in models) or "none"

    return [
        Problem(
            "plan_mismatch",
            f"the plan declares [{show(missing)}] that the page does not use, and the page uses [{show(extra)}] that the plan does not declare",
        )
    ]
