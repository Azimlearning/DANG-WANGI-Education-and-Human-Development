"""Layers L1 (provenance) and L3 (numeric cross-check) as pure functions of the Kit's audit data.

The browser reports facts (`Synapse.audit()`); everything that DECIDES lives here, where it can be tested with forged audits and no
browser. An audit is a plain dict. Nothing here trusts it more than the numbers it can recompute: the displayed text is compared with
the Kit's own formatted value, and the value is compared with an independent reference evaluated from the provenance chain.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

from api.verify.references import REFERENCES, UNIT_SI, evaluate_model, unit_factor

GROUNDED_LEAVES = ("control", "constant")
# A number in a sentence, in any of the ways a person writes one: 12, 0.04, a leading-dot .99 (previously not seen at all, so ".99 m" was never checked),
# and an exponent 5e1 (previously read as "5"). A digit run directly after a letter, digit, underscore or dot is part of an identifier or a longer
# number ("H2O", "R1", "x.5", the "3" of "1.2.3"), not a quantity.
COPY_NUMBER = re.compile(
    r"(?<![A-Za-z0-9_.])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|(?<![A-Za-z0-9_])-?\.\d+(?:[eE][+-]?\d+)?"
)
# A number is context, not a quantity, after these words ("Step 2", "Form 5") when it is a small whole number that is not followed by a
# unit, or as a list marker ("1. ") at the start of a line. Anything else must be a backed value.
COPY_CONTEXT = re.compile(
    r"(?:step|stage|part|form|tingkatan|chapter|bab|figure|rajah|table|jadual|question|soalan)\s*$", re.IGNORECASE
)
LIST_MARKER = re.compile(r"(?:^|\n)\s*$")
LIST_MARKER_AFTER = re.compile(r"^[.)]\s")
CONTEXT_MAX = 20
_UNIT_WORDS = sorted(
    {
        *UNIT_SI,
        "ohm",
        "ohms",
        "\u03a9",
        "\u00b0C",
        "K",
        "%",
        "m/s",
        "m/s2",
        "kg/m3",
        "N/m",
        "Hz",
        "mol",
        "cm3",
        "dm3",
        "m2",
        "m3",
    },
    key=len,
    reverse=True,
)
UNIT_AFTER = re.compile(r"^\s*(?:" + "|".join(re.escape(u) for u in _UNIT_WORDS) + r")(?![A-Za-z])")


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


def has_source(chain: dict) -> bool:
    """True when a control or a science model is somewhere under this chain (a bare constant is not a source of anything)."""
    if chain.get("kind") in ("control", "model"):
        return True
    return any(has_source(c) for c in (chain.get("inputs") or {}).values())


def input_unit_problems(chain: dict, audit: dict) -> list[Problem]:
    """Each science model must be fed in the unit its reference works in (a mass slider must not feed a force input)."""
    out: list[Problem] = []
    if chain.get("kind") == "model" and chain.get("id") in REFERENCES:
        ref = REFERENCES[chain["id"]]
        for name, child in (chain.get("inputs") or {}).items():
            have = _chain_unit(child, audit)
            want = ref.input_units.get(name)
            if want is not None and have is not None and have != want:
                out.append(
                    Problem(
                        "wrong_input_unit",
                        f"{chain['id']} input '{name}' is in {have!r} but the model works in {want!r}",
                    )
                )
    if chain.get("kind") == "convert":
        # A conversion multiplies by the factor for `from` to `to`. That is only right if the source really is in `from`: convert(metres, "mm", "m")
        # has a correct factor, passes the unit label check (it reports `to`) and is recomputed identically by L3, yet shows a value 1000 times too
        # small. An unknown source unit fails closed: a conversion of something whose unit nothing declares cannot be told from this.
        source = (chain.get("inputs") or {}).get("x")
        have = _chain_unit(source, audit) if isinstance(source, dict) else None
        if have != chain.get("from"):
            out.append(
                Problem(
                    "wrong_conversion_source",
                    f"converts from {chain.get('from')!r} to {chain.get('to')!r} but its source is in {have!r}",
                )
            )
    for child in (chain.get("inputs") or {}).values():
        out += input_unit_problems(child, audit)
    return out


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


def all_chains(audit: dict) -> list[tuple[str, dict]]:
    """Every value the page shows or draws, as (what it is, its provenance chain): readouts, table columns, graph series and scenes."""
    found = [(f"readout '{r['label']}'", r["chain"]) for r in audit.get("readouts", [])]
    found += [(f"{x['kind']} '{x['label']}'", x["chain"]) for x in audit.get("series", [])]
    found += [(f"{w['kind']} '{w['id']}'", w["chain"]) for w in audit.get("widgets", []) if w.get("chain")]
    return found


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
    for _, chain in all_chains(audit):
        for _, params in models_in(chain):
            values += [v for _, v in params]
    return values


def copy_number_problems(audit: dict) -> list[Problem]:
    backed = backed_numbers(audit)
    out: list[Problem] = []
    for entry in audit.get("copy", []):
        text = unicodedata.normalize(
            "NFKC", entry["text"]
        )  # fullwidth, Arabic-Indic and similar digits become ASCII first
        for m in COPY_NUMBER.finditer(text):
            before, after = text[: m.start()], text[m.end() :]
            value = float(m.group())
            small_whole = value == int(value) and 0 <= value <= CONTEXT_MAX
            if small_whole and not UNIT_AFTER.match(after):
                if COPY_CONTEXT.search(before):
                    continue
                if LIST_MARKER.search(before) and LIST_MARKER_AFTER.match(after):
                    continue
            if not any(_close(value, b) for b in backed):
                out.append(
                    Problem(
                        "unbacked_copy_number",
                        f"the text states {m.group()} which is not a control value, a constant or a model parameter: {text[:80]!r}",
                    )
                )
    return out


# ── L1 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────


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


REQUIRED_KEYS = (
    "kitVersion",
    "intact",
    "controls",
    "readouts",
    "readoutElements",
    "constants",
    "series",
    "actions",
    "forgedActions",
    "copy",
    "ownedMismatches",
    "unownedNumbers",
    "unownedAttributeNumbers",
    "forbidden",
    "shadowRoots",
    "widgets",
)


def _value_problems(what: str, unit: str, chain: dict, audit: dict) -> list[Problem]:
    """The chain and unit rules shared by readouts, table columns and graph series."""
    out: list[Problem] = []
    found = chain_problem(chain)
    if found:
        return [Problem(found.rule, f"{what}: {found.reason}")]
    if not has_source(chain):
        out.append(
            Problem(
                "constant_readout",
                f"{what} shows a fixed value no control or science model produced; state it in a sentence instead",
            )
        )
    shown = _chain_unit(chain, audit)
    if shown is not None and shown != unit:
        out.append(Problem("wrong_unit", f"{what} is labelled {unit!r} but its value is in {shown!r}"))
    for p in input_unit_problems(chain, audit):
        out.append(Problem(p.rule, f"{what}: {p.reason}"))
    return out


# The model each kind of scene may draw. A scene is a picture of a model's number; one bound to anything else is a picture the audit cannot ground.
SCENE_MODELS = {"spring": "mechanics.hookes"}
SCENE_FILL_MIN = 0.5
"""A scene's drawing scale must be no less than the model's output at the controls' maximum and no more than twice it (the picture is then nearly full and never clipped)."""


def _scene_scale_problems(w: dict, chain: dict, audit: dict) -> list[Problem]:
    """The drawing scale the page gave a scene, against the model's own output with every control at its maximum (from the independent reference)."""
    controls_at_max = {c["id"]: float(c["max"]) for c in audit.get("controls", [])}
    constants = {c["label"]: float(c["value"]) for c in audit.get("constants", [])}
    try:
        peak = evaluate_chain(chain, controls_at_max, constants)
    except (ValueError, KeyError):
        return []  # an unevaluable chain is refused by the checks above
    full = w.get("full")
    if not isinstance(full, (int, float)) or isinstance(full, bool) or not math.isfinite(full) or full <= 0 or not (SCENE_FILL_MIN <= peak / full <= 1 + 1e-9):
        return [Problem("scene_scale", f"the {w.get('id')} scene is drawn to a scale of {full!r} but its model reaches {peak:g} at the controls' maximum")]
    return []


def widget_problems(audit: dict) -> list[Problem]:
    """The mass hangers and scenes the Kit built: each must report itself intact, a scene must draw the model it is registered for, and a hanger must have as many masses as the Kit made."""
    out: list[Problem] = []
    for w in audit["widgets"]:
        for text in [*w.get("problems", []), *w.get("layout", [])]:
            out.append(Problem("widget_tampered", text))
        if w.get("kind") == "scene":
            chain = w.get("chain") or {}
            if chain.get("kind") != "model" or chain.get("id") != SCENE_MODELS.get(w.get("id", "")):
                out.append(Problem("scene_ungrounded", f"the {w.get('id')} scene does not draw the output of {SCENE_MODELS.get(w.get('id', ''))}"))
            else:
                found = chain_problem(chain)
                if found:
                    out.append(Problem(found.rule, f"the {w.get('id')} scene: {found.reason}"))
                out += [Problem(p.rule, f"the {w.get('id')} scene: {p.reason}") for p in input_unit_problems(chain, audit)]
                out += _scene_scale_problems(w, chain, audit)
    return out


def l1_problems(audit: dict | None) -> list[Problem]:
    """Layer L1 on one audit snapshot. Empty means the page's numbers are grounded and unaltered at this moment."""
    if not isinstance(audit, dict):
        return [Problem("kit_missing", "the page did not report a Kit audit (is window.Synapse the Kit?)")]
    missing = [k for k in REQUIRED_KEYS if k not in audit]
    if missing:
        # A report that leaves out a section is not a report of "nothing found": fail closed.
        return [Problem("malformed_audit", f"the Kit audit is missing {missing}")]
    out: list[Problem] = []
    if not audit["intact"]:
        out.append(Problem("kit_not_intact", "window.Synapse is not the sealed Kit object"))
    if audit["readoutElements"] != len(audit["readouts"]):
        out.append(
            Problem(
                "unregistered_readout",
                f"the page has {audit['readoutElements']} readout elements but the Kit made {len(audit['readouts'])}",
            )
        )
    for r in audit["readouts"]:
        out += _value_problems(f"readout '{r['label']}'", r["unit"], r["chain"], audit)
        if r["displayed"] != r["expected"]:
            out.append(
                Problem(
                    "readout_mismatch",
                    f"readout '{r['label']}' shows {r['displayed']!r} but its value is {r['expected']!r}",
                )
            )
    for x in audit["series"]:
        out += _value_problems(f"{x['kind']} '{x['label']}'", x["unit"], x["chain"], audit)
    for c in audit["controls"]:
        try:
            gap = abs(float(c["inputValue"]) - float(c["value"]))
        except ValueError:
            gap = math.inf
        if not gap <= float(c["step"]) / 2 + 1e-9:
            out.append(
                Problem(
                    "control_mismatch",
                    f"control '{c['id']}' holds {c['value']} but its input shows {c['inputValue']!r}",
                )
            )
    if audit["forgedActions"]:
        out.append(Problem("forged_action", "a button claims to be a Kit action but no Kit component made it"))
    for f in audit["forbidden"]:
        out.append(Problem("forbidden_markup", f"{f['what']} ({f['element']}) can show a number the audit cannot read"))
    for m in audit["ownedMismatches"]:
        out.append(
            Problem(
                "owned_changed",
                f"a <{m['tag']}> the Kit made was edited: expected {m['expected']!r}, found {m['actual']!r}",
            )
        )
    for a in audit["unownedAttributeNumbers"]:
        out.append(
            Problem(
                "unowned_attribute_number",
                f"{a['attribute']} on <{a['element']}> holds a number the Kit did not set: {a['value']!r}",
            )
        )
    if audit["shadowRoots"]:
        out.append(Problem("shadow_root", "an element has a shadow root; its content cannot be audited"))
    out += widget_problems(audit)
    for u in audit["unownedNumbers"]:
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
    for x in audit.get("series", []):
        if chain_problem(x["chain"]) is not None:
            continue
        what = f"{x['kind']} '{x['label']}'"
        try:
            expected = evaluate_chain(x["chain"], controls, constants)
        except (ValueError, KeyError) as exc:
            problems.append(
                Problem("reference_error", f"{what}: the reference could not be evaluated at {controls}: {exc}")
            )
            continue
        compared += 1
        if not math.isclose(float(x["value"]), expected, rel_tol=1e-9, abs_tol=1e-12):
            problems.append(
                Problem(
                    "numeric_mismatch",
                    f"{what} holds {x['value']} but the independent reference gives {expected} at {controls}",
                )
            )
        for px, py in x.get("points") or []:
            try:
                want = evaluate_chain(x["chain"], {**controls, x["xControl"]: float(px)}, constants)
            except (ValueError, KeyError) as exc:
                problems.append(Problem("reference_error", f"{what}: the reference failed at x={px}: {exc}"))
                break
            compared += 1
            if not math.isclose(float(py), want, rel_tol=1e-9, abs_tol=1e-12):
                problems.append(
                    Problem(
                        "numeric_mismatch",
                        f"{what} draws {py} at {x['xControl']}={px} but the independent reference gives {want}",
                    )
                )
                break
    return problems, compared


def plan_problems(audit: dict, plan_models: list[dict] | None) -> list[Problem]:
    """The models the page really uses must be exactly the ones the plan declares, with the same parameters."""
    if plan_models is None:
        return []
    used = {m for _, chain in all_chains(audit) for m in models_in(chain)}
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
