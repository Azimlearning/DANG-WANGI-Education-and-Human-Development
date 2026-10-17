"""The fail-check registry: every refusal the pipeline can produce has a stable code, a layer, a severity, a repair route, a one-line hint for
the model and a plain message for the student. A test (test_failchecks.py) reads the sources and fails if the verifier, the post-processor, the
plan checks or the fill checks can emit a rule that is not listed here, or if an entry here can no longer be emitted. So this file cannot drift,
and the pattern packs' "failure modes to avoid" sections are generated from it (prompts.py).

Repair routes: `deterministic` (code fixes it), `retry_plan` (ask the planner once with the named issue), `retry_fill` (ask for the slot again),
`assembler` (a fix in our code, not the model's), `free_lane` (fall to the labelled Free lane), `text_only` (answer in words), `none` (a bug in
our own pipeline, never retried).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["block", "degrade"]
Repair = Literal["deterministic", "retry_plan", "retry_fill", "assembler", "free_lane", "text_only", "none"]


@dataclass(frozen=True)
class FailCheck:
    rule: str
    code: str
    layer: str
    severity: Severity
    repair: Repair
    model_hint: str
    student_message: str


_GENERIC = "This Environment could not be made safely, so you are getting the written answer instead."


def _e(
    rule: str, code: str, layer: str, severity: Severity, repair: Repair, hint: str, student: str = _GENERIC
) -> tuple[str, FailCheck]:
    return rule, FailCheck(rule, code, layer, severity, repair, hint, student)


_ENTRIES = [
    # L0 and post-process
    _e(
        "forbidden_api",
        "L0-001",
        "L0 scan",
        "block",
        "retry_plan",
        "Do not use network, storage, navigation, eval, timers with strings or DOM injection.",
    ),
    _e("script_source", "L0-002", "L0 scan", "block", "assembler", "Load scripts only from /vendor/ on this origin."),
    _e("link_href", "L0-003", "L0 scan", "block", "assembler", "Do not link to other documents or origins."),
    _e(
        "kit_first",
        "L0-004",
        "L0 scan",
        "block",
        "assembler",
        "The Kit script must be the first and only script before the page script.",
    ),
    _e(
        "kit_lane",
        "L0-005",
        "L0 scan",
        "block",
        "retry_fill",
        "Do not draw numbers with canvas, images, CSS content, fonts or shadow DOM.",
    ),
    _e("comment", "PP-001", "post-process", "block", "assembler", "Close every comment; none are needed."),
    _e(
        "markup_declaration",
        "PP-002",
        "post-process",
        "block",
        "assembler",
        "Use no CDATA, processing instructions or stray declarations.",
    ),
    _e("single_document", "PP-003", "post-process", "block", "assembler", "Produce exactly one HTML document."),
    _e(
        "csp_position",
        "PP-004",
        "post-process",
        "block",
        "none",
        "Our policy must be first in the head; this is a pipeline bug.",
    ),
    _e(
        "size_cap", "PP-005", "post-process", "block", "retry_plan", "Make the page smaller: fewer parts, shorter text."
    ),
    # kit, label, grounding, plan (mint)
    _e("unknown_version", "KIT-001", "kit", "block", "none", "The Kit version is not built; this is a pipeline bug."),
    _e("version_mismatch", "KIT-002", "kit", "block", "assembler", "Load the Kit version the plan names, once."),
    _e(
        "stale_kit",
        "KIT-003",
        "gate",
        "block",
        "none",
        "The stored Environment was made with a Kit that has since changed; regenerate it.",
    ),
    _e(
        "citation_unproved",
        "LAB-005",
        "label",
        "block",
        "retry_plan",
        "A citation marked verified must quote its page word for word; quote the page again or drop the claim.",
    ),
    _e(
        "no_evidence",
        "LAB-006",
        "label",
        "block",
        "none",
        "kit-verified needs the corpus to re-prove citations and none is configured.",
    ),
    _e("no_citation", "LAB-001", "label", "block", "none", "State a source, or an explicit UNVERIFIED citation."),
    _e("needs_human", "LAB-002", "label", "block", "none", "Only a person can grant this label."),
    _e("free_lane", "LAB-003", "label", "block", "none", "A Free-lane Environment cannot be kit-verified."),
    _e("ungrounded", "LAB-004", "label", "block", "none", "A kit-verified label needs a verified textbook citation."),
    _e(
        "plan_missing",
        "PLN-100",
        "plan",
        "block",
        "none",
        "A Kit-lane page needs the plan's list of science models; this is a pipeline bug.",
    ),
    _e(
        "unreachable",
        "KIT-004",
        "kit",
        "block",
        "none",
        "The Kit script could not be loaded by the harness; this is a pipeline bug.",
    ),
    # render harness
    _e(
        "ready",
        "RND-001",
        "render",
        "block",
        "retry_plan",
        "The page must call Synapse.bridge.ready() once and run without errors.",
    ),
    _e("navigation", "RND-002", "render", "block", "free_lane", "The page must never navigate or open another window."),
    _e("harness_error", "RND-003", "render", "block", "none", "The harness lost the page; treat as a refusal."),
    _e(
        "errors",
        "RND-004",
        "render",
        "block",
        "retry_plan",
        "Fix the runtime error; the page threw or logged an error.",
    ),
    _e(
        "blocked_request",
        "RND-005",
        "render",
        "block",
        "retry_plan",
        "The page tried to load something outside this origin; remove it.",
    ),
    _e(
        "runtime_violation",
        "RND-006",
        "render",
        "block",
        "none",
        "The Kit's own self-check tripped; something changed what the Kit drew.",
    ),
    _e("no_controls", "L2-001", "L2 behaviour", "block", "retry_plan", "Add at least one slider."),
    _e(
        "undeclared_control",
        "L2-002",
        "L2 behaviour",
        "block",
        "retry_fill",
        "Every interactive element must be a Kit control or action.",
    ),
    _e("duplicate_control", "L2-003", "L2 behaviour", "block", "retry_plan", "Give every control its own id."),
    _e(
        "dead_control",
        "L2-004",
        "L2 behaviour",
        "block",
        "retry_plan",
        "Every slider must feed a model that a readout shows.",
    ),
    _e(
        "unstable_readout",
        "L2-005",
        "L2 behaviour",
        "block",
        "retry_fill",
        "Readouts must change only when a control changes.",
    ),
    _e(
        "a11y", "A11Y-001", "accessibility", "block", "retry_plan", "Give every control and readout an accessible name."
    ),
    _e("touch_target", "A11Y-002", "accessibility", "block", "assembler", "Controls must be at least 44 px tall."),
    _e("horizontal_overflow", "A11Y-003", "accessibility", "block", "retry_plan", "Nothing may be wider than 360 px."),
    # L1 provenance
    _e("kit_missing", "L1-001", "L1 provenance", "block", "none", "window.Synapse is missing; the Kit did not load."),
    _e("kit_not_intact", "L1-002", "L1 provenance", "block", "none", "window.Synapse is not the sealed Kit."),
    _e("malformed_audit", "L1-003", "L1 provenance", "block", "none", "The Kit's audit report was incomplete."),
    _e(
        "ungrounded_readout",
        "L1-004",
        "L1 provenance",
        "block",
        "retry_plan",
        "Every readout must come from a model fed by a control or a constant.",
    ),
    _e(
        "unaudited_arithmetic",
        "L1-005",
        "L1 provenance",
        "block",
        "retry_plan",
        "Do no arithmetic in the page; use Synapse.convert for a unit change.",
    ),
    _e(
        "unknown_model",
        "L1-006",
        "L1 provenance",
        "block",
        "retry_plan",
        "Use only science models listed in the Kit manifest.",
    ),
    _e(
        "constant_readout",
        "L1-007",
        "L1 provenance",
        "block",
        "retry_plan",
        "Do not show a fixed value as a readout; state it in a sentence.",
    ),
    _e(
        "wrong_unit",
        "L1-008",
        "L1 provenance",
        "block",
        "deterministic",
        "Label the readout with the unit the model returns.",
    ),
    _e(
        "wrong_input_unit",
        "L1-009",
        "L1 provenance",
        "block",
        "retry_plan",
        "Feed each model input from a control in the unit the model works in.",
    ),
    _e(
        "bad_unit_factor",
        "L1-010",
        "L1 provenance",
        "block",
        "none",
        "A unit conversion used a wrong factor; the Kit is at fault.",
    ),
    _e("readout_mismatch", "L1-011", "L1 provenance", "block", "retry_fill", "Do not edit a readout's text."),
    _e("owned_changed", "L1-012", "L1 provenance", "block", "retry_fill", "Do not edit text the Kit made."),
    _e(
        "unowned_number",
        "L1-013",
        "L1 provenance",
        "block",
        "retry_fill",
        "Put numbers in Synapse.text sentences, not in the DOM.",
    ),
    _e(
        "unowned_attribute_number",
        "L1-014",
        "L1 provenance",
        "block",
        "retry_fill",
        "Do not put numbers in aria or title attributes.",
    ),
    _e(
        "unbacked_copy_number",
        "L1-015",
        "L1 provenance",
        "block",
        "retry_plan",
        "A number in a sentence must be a slider value, a constant or a model setting.",
    ),
    _e("shadow_root", "L1-016", "L1 provenance", "block", "retry_fill", "Do not use shadow DOM."),
    _e("forged_action", "L1-017", "L1 provenance", "block", "retry_fill", "Do not make your own buttons."),
    _e(
        "forbidden_markup",
        "L1-018",
        "L1 provenance",
        "block",
        "retry_fill",
        "Do not use canvas, media, list counters, CSS images or fonts.",
    ),
    _e(
        "unregistered_readout",
        "L1-019",
        "L1 provenance",
        "block",
        "retry_fill",
        "Make readouts only with Synapse.readout.",
    ),
    _e("control_mismatch", "L1-020", "L1 provenance", "block", "retry_fill", "A control must hold the value it shows."),
    _e(
        "wrong_conversion_source",
        "L1-021",
        "L1 provenance",
        "block",
        "retry_plan",
        "Convert from the unit the value is really in: a conversion's starting unit must be the unit of its source.",
    ),
    # L3 reference and plan
    _e(
        "numeric_mismatch",
        "L3-001",
        "L3 reference",
        "block",
        "none",
        "A displayed value disagrees with the independent reference; the Kit model is at fault.",
    ),
    _e(
        "reference_error",
        "L3-002",
        "L3 reference",
        "block",
        "retry_plan",
        "The reference could not be computed at a control position; keep inputs inside the model's domain.",
    ),
    _e(
        "non_finite_readout",
        "L3-003",
        "L3 reference",
        "block",
        "retry_plan",
        "A readout showed a value that is not a number.",
    ),
    _e(
        "plan_mismatch",
        "L3-004",
        "L3 reference",
        "block",
        "assembler",
        "The page must use exactly the plan's models and parameters.",
    ),
    # gate
    _e("not_found", "GATE-001", "gate", "block", "none", "No such verified Environment."),
    _e("hash_mismatch", "GATE-002", "gate", "block", "none", "The stored page no longer matches its hash."),
    _e("csp_mismatch", "GATE-003", "gate", "block", "none", "The stored page's policy is not the current one."),
    _e(
        "withdrawn",
        "GATE-005",
        "gate",
        "block",
        "none",
        "This Environment was withdrawn by the operator; it is not delivered.",
        "This Environment was taken down while it is being corrected, so you are getting the written answer.",
    ),
    _e("unattested", "GATE-006", "gate", "block", "none", "The stored row has no valid signature from this verifier."),
    _e("bad_record", "GATE-004", "gate", "block", "none", "The stored record is unusable."),
    # plan checks
    _e("PLAN-001", "PLAN-001", "plan", "block", "retry_plan", "Return JSON that matches the plan schema exactly."),
    _e("PLAN-002", "PLAN-002", "plan", "block", "retry_plan", "Use only science models listed in the Kit manifest."),
    _e(
        "PLAN-003",
        "PLAN-003",
        "plan",
        "block",
        "retry_plan",
        "Give each model exactly its parameters, inside its domain.",
    ),
    _e(
        "PLAN-004",
        "PLAN-004",
        "plan",
        "block",
        "retry_plan",
        "Bind each model input to a control or constant in the right unit.",
    ),
    _e("PLAN-005", "PLAN-005", "plan", "block", "retry_plan", "Keep control ranges inside the model's domain."),
    _e("PLAN-006", "PLAN-006", "plan", "block", "retry_plan", "Point readouts, graphs and columns at ids that exist."),
    _e(
        "PLAN-007",
        "PLAN-007",
        "plan",
        "block",
        "retry_plan",
        "Label every value with the unit the model returns (or a valid conversion).",
    ),
    _e(
        "PLAN-008",
        "PLAN-008",
        "plan",
        "block",
        "retry_plan",
        "Remove numbers from sentences unless they are slider values, constants or model settings.",
    ),
    _e("PLAN-009", "PLAN-009", "plan", "block", "retry_plan", "Plan only with components in the Kit manifest."),
    _e("PLAN-010", "PLAN-010", "plan", "block", "deterministic", "Shorten the words and keep grids small."),
    _e("PLAN-011", "PLAN-011", "plan", "block", "retry_plan", "Give every control, constant and model its own id."),
    _e(
        "PLAN-012",
        "PLAN-012",
        "plan",
        "block",
        "retry_plan",
        "Include every part the pattern needs and none it cannot take.",
    ),
    _e(
        "PLAN-013",
        "PLAN-013",
        "plan",
        "block",
        "retry_plan",
        "Make the concept check's correct index one of its options.",
    ),
    _e(
        "PLAN-016",
        "PLAN-016",
        "plan",
        "block",
        "retry_plan",
        "Use a model that is registered for the question's topic.",
    ),
    _e(
        "PLAN-017",
        "PLAN-017",
        "plan",
        "block",
        "retry_plan",
        "Show more digits so the control visibly changes a readout, or widen its range.",
    ),
    _e("PLAN-015", "PLAN-015", "plan", "block", "retry_plan", "Keep the final volume at or above the starting volume."),
    _e("PLAN-014", "PLAN-014", "plan", "block", "deterministic", "Start each control inside its range."),
    # fill checks
    _e("FILL-001", "FILL-001", "fill", "degrade", "retry_fill", "Keep the fill short."),
    _e("FILL-002", "FILL-002", "fill", "degrade", "retry_fill", "Use only Kit calls."),
    _e("FILL-003", "FILL-003", "fill", "degrade", "retry_fill", "Call only the Kit components this slot allows."),
    _e("FILL-004", "FILL-004", "fill", "degrade", "retry_fill", "Use only the names the page defines."),
    _e("FILL-005", "FILL-005", "fill", "degrade", "retry_fill", "Write a complete, balanced fill."),
    _e("FILL-006", "FILL-006", "fill", "degrade", "retry_fill", "Write JavaScript only, no tags."),
    # pipeline-level
    _e(
        "GAP",
        "PIPE-001",
        "assemble",
        "degrade",
        "free_lane",
        "The skeleton cannot take this plan; the part falls to the Free lane.",
    ),
    _e(
        "BUDGET",
        "PIPE-002",
        "pipeline",
        "degrade",
        "text_only",
        "The request used its call budget; answer in words.",
        "This question used up the steps it is allowed, so you are getting the written answer.",
    ),
    _e(
        "INTAKE",
        "PIPE-003",
        "intake",
        "block",
        "text_only",
        "The question could not be accepted.",
        "That question cannot be answered here. Try a science question from your Form 4 or Form 5 textbook.",
    ),
]

REGISTRY: dict[str, FailCheck] = dict(_ENTRIES)


def get(rule: str) -> FailCheck:
    """The entry for a rule; an unknown rule is a pipeline bug and reads as one rather than being invented."""
    return REGISTRY.get(rule) or FailCheck(
        rule, "PIPE-999", "pipeline", "block", "none", "Unregistered rule.", _GENERIC
    )


def failure_modes(layers: tuple[str, ...]) -> list[FailCheck]:
    """The entries a pattern pack lists as 'failure modes to avoid': model-fixable ones in the given layers."""
    return [
        f for f in REGISTRY.values() if f.layer in layers and f.repair in ("retry_plan", "retry_fill", "deterministic")
    ]
