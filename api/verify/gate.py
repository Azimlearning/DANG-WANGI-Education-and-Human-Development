# Pattern from Azimlearning/Arcana-v2, api/genui/validate.py (the lab branch near line 805) @ 21c6dcf5, and web/lib/labFrame.ts:
# the delivery gate re-derives the block from the STORED record and re-checks it, instead of trusting that it was checked once.
# Read the relevant parts in full and rewritten for Environments.
"""The delivery gate (hard constraint 1): the last server-side check before an Environment reaches the client.

It does not take a `VerifiedEnvironment` from memory. It reads the stored row by id, re-hashes the HTML, re-runs the L0 scan,
checks the injected CSP against the configured origin, checks the label rules and that the Kit version is still built, and only
then builds the `EnvironmentBlock`. A tampered row, a stale Kit, a changed origin and a forged label are all refused here.
The browser then re-hashes `html` against `htmlSha256` before rendering (web/lib/hash.ts).
"""

from __future__ import annotations

from pathlib import Path

from api import postprocess
from api.schema.generated import BlockMeta, Citation, EnvironmentBlock
from api.verify import scan as l0
from api.verify.mint import Evidence, VerificationFailed, guard_label, html_sha256, kit_bundle_sha256
from api.verify.store import SqliteEnvironmentStore

LIMITS: dict[str, str] = {
    "model-checked": (
        "Checked by code, not by a person. No textbook source has been verified, so the science may not match the syllabus."
    ),
    "kit-verified": "Checked by code against audited Kit models with a verified textbook source. A person has not reviewed it.",
    "reviewed": "A person checked it against the textbook page.",
    "canonical": "A person checked it against the textbook page and approved it.",
}


def checked_summary(checked: dict, label: str) -> dict:
    """The wire `CheckedSummary` from the stored record. Raises KeyError or ValueError on an unusable record."""
    return {
        "layers": [str(x) for x in checked["layers"]],
        "controlsExercised": int(checked["controls_exercised"]),
        "gridPoints": int(checked["grid_points"]),
        "referenceCases": int(checked["reference_cases"]),
        "readouts": int(checked["readouts"]),
        "models": [
            {"id": str(m["id"]), "params": {str(k): float(v) for k, v in m["params"].items()}}
            for m in checked["models"]
        ],
        "limits": LIMITS[label],
    }


def deliver(
    store: SqliteEnvironmentStore, env_id: str, *, public_origin: str, kit_dist: Path, evidence: Evidence | None = None
) -> EnvironmentBlock:
    """Return the block for `env_id`, or raise `VerificationFailed` with stage 'gate'."""
    record = store.get_record(env_id)
    if record is None:
        raise VerificationFailed("gate", "not_found", f"no verified environment '{env_id}'")

    actual = html_sha256(record.html)
    if actual != record.html_sha256 or not record.env_id.endswith(actual[:12]):
        raise VerificationFailed("gate", "hash_mismatch", "the stored HTML does not match its recorded hash")

    if not store.attestation_ok(record):
        raise VerificationFailed(
            "gate", "unattested", "the stored row was not written by this verifier (bad or missing signature)"
        )

    hit = l0.scan(record.html)
    if hit is not None:
        raise VerificationFailed("gate", hit.rule, hit.reason)

    if store.status(env_id) != "active":
        raise VerificationFailed("gate", "withdrawn", f"Environment '{env_id}' was withdrawn and is not delivered")

    if not postprocess.csp_is_first(record.html, public_origin):
        raise VerificationFailed(
            "gate",
            "csp_mismatch",
            "the stored CSP is missing, duplicated, not the first element, or does not name the configured PUBLIC_ORIGIN",
        )

    current = kit_bundle_sha256(kit_dist, record.kit_version)
    if current is None or current != record.kit_sha256:
        raise VerificationFailed(
            "gate",
            "stale_kit",
            f"Kit {record.kit_version} is not built, or its bytes changed since this was verified; re-verify",
        )

    citations = tuple(Citation.model_validate(c) for c in record.citations)
    try:
        guard_label(record.lane, record.label, citations, evidence)
    except VerificationFailed as failure:
        raise VerificationFailed("gate", failure.rule, failure.reason) from failure

    try:
        checked = checked_summary(record.checked, record.label)
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationFailed("gate", "bad_record", f"the stored 'checked' record is unusable: {exc}") from exc

    return EnvironmentBlock.model_validate(
        {
            "type": "Environment",
            "id": record.env_id,
            "meta": BlockMeta(status="ready", error=None).model_dump(),
            "title": record.title,
            "lane": record.lane,
            "label": record.label,
            "kitVersion": record.kit_version,
            "htmlSha256": record.html_sha256,
            "html": record.html,
            "citations": [c.model_dump() for c in citations],
            "checked": checked,
            "planSummary": record.plan_summary,
        }
    )
