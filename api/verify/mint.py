# Ported from Azimlearning/Arcana-v2, api/labs/verifier.py @ 21c6dcf5 (the VerifiedArtifact mint). Read in full and adapted:
# the closure-held token, the frozen slots class that cannot be subclassed, and the single private issuer are kept; the
# lab-specific checks (contract, grid, fuzz, node runner) are replaced by this repo's layers (post-process rules, L0 scan,
# render harness) and by the label and grounding guard below.
"""The verifier and the mint: the only code that can create a `VerifiedEnvironment` (hard constraint 1).

`verify_environment()` runs, in order: the label and grounding guard, the Kit version check, the post-process rules (single
document, the L0 scan, viewport, charset, CSP, size cap), then the render harness. Only if every stage passes does it issue a
`VerifiedEnvironment`. Any failure is a `VerificationFailed` naming the stage, the rule and the reason.

`VerifiedEnvironment` is created through a function holding the mint token in a closure (not a module attribute), and cannot be
subclassed, changed or copied. That is hardening, not a language guarantee: Python cannot stop code in the same process from
forging an object, and this process never runs generated code (the browser does, in a harness). The lines downstream do not rely
on it: the store ties the id to the hash, and the delivery gate re-hashes and re-checks the stored HTML. A test scans the source
tree to prove the issuer is referenced only in this file.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from api import postprocess
from api.schema.generated import Citation, Lane, TrustLabel
from api.verify.render import INTERACTION_SECONDS, render_check

ALLOWED_LABELS: frozenset[str] = frozenset({"model-checked"})
"""D-21. `kit-verified` is unreachable until a citation can be verified against the corpus (P2); `reviewed` and `canonical` need a
human (P5). Widening this set is a declared change with an ADR, not an edit."""

_KIT_VERSIONS_IN_HTML = re.compile(r"/vendor/kit/(\d+\.\d+\.\d+)/")


class VerificationFailed(Exception):
    """An Environment did not pass: `stage` names the layer (label, kit, postprocess, scan, render), `rule` the check."""

    def __init__(self, stage: str, rule: str, reason: str):
        super().__init__(f"{stage}/{rule}: {reason}")
        self.stage = stage
        self.rule = rule
        self.reason = reason


class MintRefused(RuntimeError):
    """A `VerifiedEnvironment` was asked for without going through the verifier."""


@dataclass(frozen=True)
class Checked:
    """What was actually checked, kept with the record so the student-facing limits are not invented later."""

    layers: tuple[str, ...]
    controls_exercised: int
    readouts: int
    grid_points: int
    reference_cases: int
    models: tuple[tuple[str, tuple[tuple[str, float], ...]], ...]
    """Each science micro-model used, as (id, ((parameter, value), ...))."""
    interaction_seconds: float


_FIELDS = (
    "env_id",
    "title",
    "lane",
    "label",
    "kit_version",
    "kit_sha256",
    "html",
    "html_sha256",
    "citations",
    "plan_summary",
    "checked",
)


def _make_environment_class() -> tuple[type, Any]:
    token = object()  # held here, in a closure: no module attribute carries it

    class VerifiedEnvironment:
        """What the verifier mints: an Environment that passed every stage, with its hash and what was checked."""

        __slots__ = (*_FIELDS, "_frozen")

        def __init_subclass__(cls, **kwargs: Any) -> None:
            raise TypeError("a VerifiedEnvironment cannot be subclassed")

        def __init__(self, *, _mint: object = None, **fields: Any):
            if _mint is not token:
                raise MintRefused("a VerifiedEnvironment can only be created by the verifier")
            if set(fields) != set(_FIELDS):
                raise MintRefused("a VerifiedEnvironment needs exactly its fields")
            for name, value in fields.items():
                object.__setattr__(self, name, value)
            object.__setattr__(self, "_frozen", True)

        def __setattr__(self, name: str, value: Any) -> None:
            raise AttributeError("a VerifiedEnvironment cannot be changed")

        def __delattr__(self, name: str) -> None:
            raise AttributeError("a VerifiedEnvironment cannot be changed")

        def __copy__(self) -> Any:
            raise TypeError("a VerifiedEnvironment cannot be copied")

        def __deepcopy__(self, memo: Any) -> Any:
            raise TypeError("a VerifiedEnvironment cannot be copied")

        def __reduce__(self) -> Any:
            raise TypeError("a VerifiedEnvironment cannot be pickled")

        def __repr__(self) -> str:
            return f"VerifiedEnvironment({self.env_id})"  # type: ignore[attr-defined]

    def issue(**fields: Any) -> Any:
        return VerifiedEnvironment(_mint=token, **fields)

    return VerifiedEnvironment, issue


_environment_class, _issue = _make_environment_class()
if TYPE_CHECKING:  # the static view of the class the factory makes

    class VerifiedEnvironment:
        env_id: str
        title: str
        lane: Lane
        label: TrustLabel
        kit_version: str
        kit_sha256: str
        html: str
        html_sha256: str
        citations: tuple[Citation, ...]
        plan_summary: str
        checked: Checked

        def __init__(self, **fields: Any) -> None: ...

else:
    VerifiedEnvironment = _environment_class
"""The class (public: it is the type the delivery path accepts) and the one function that creates one (`_issue`, private to this
module; a test scans the repository for any other use of it)."""


def kit_bundle_sha256(kit_dist: Path, kit_version: str) -> str | None:
    """SHA-256 of the built Kit bundle for `kit_version`, or None when it is not built. Stored with each Environment so a Kit whose
    bytes changed under the same semver makes stored Environments stale (hard constraint 6)."""
    core = kit_dist / kit_version / "core.js"
    return hashlib.sha256(core.read_bytes()).hexdigest() if core.is_file() else None


def html_sha256(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def env_id_for(slug: str, sha: str) -> str:
    return f"{slug}-{sha[:12]}"


def guard_label(lane: str, label: str, citations: tuple[Citation, ...]) -> None:
    """Hard constraints 3 and 4 as code. Today only `model-checked` is reachable; the rules below stay so that widening the
    allowed set later cannot also widen what a label promises."""
    if not citations:
        # Hard constraints 4 and 11: where no source exists the Environment says so. An empty list says nothing at all.
        raise VerificationFailed("grounding", "no_citation", "state a source, or an explicit UNVERIFIED citation")
    if label in ("reviewed", "canonical"):
        raise VerificationFailed("label", "needs_human", f"'{label}' needs human review; the verifier cannot grant it")
    if label == "kit-verified":
        if lane == "free":
            raise VerificationFailed("label", "free_lane", "a Free-lane Environment cannot be 'kit-verified'")
        if not any(c.verified for c in citations):
            raise VerificationFailed("label", "ungrounded", "'kit-verified' needs a verified textbook citation")
    if label not in ALLOWED_LABELS:
        raise VerificationFailed(
            "label",
            "unreachable",
            f"label '{label}' is not mintable yet (D-21: it needs a verified citation or a human)",
        )


def verify_environment(
    *,
    slug: str,
    title: str,
    raw_html: str,
    lane: Lane,
    label: TrustLabel,
    kit_version: str,
    citations: list[Citation],
    plan_summary: str,
    public_origin: str,
    kit_dist: Path,
    interaction_seconds: float = INTERACTION_SECONDS,
    plan_models: list[dict] | None = None,
) -> VerifiedEnvironment:
    """Check `raw_html` end to end and return the minted `VerifiedEnvironment`, or raise `VerificationFailed`."""
    cited = tuple(citations)
    guard_label(lane, label, cited)

    kit_sha = kit_bundle_sha256(kit_dist, kit_version)
    if kit_sha is None:
        raise VerificationFailed("kit", "unknown_version", f"Kit {kit_version} is not built in {kit_dist}")
    used = set(_KIT_VERSIONS_IN_HTML.findall(raw_html))
    if used - {kit_version}:
        raise VerificationFailed(
            "kit", "version_mismatch", f"HTML loads Kit {sorted(used)} but the plan says {kit_version}"
        )

    processed = postprocess.run(
        raw_html, public_origin=public_origin, kit_version=None if lane == "free" else kit_version
    )
    if isinstance(processed, postprocess.PostprocessReject):
        raise VerificationFailed(processed.stage, processed.rule, processed.reason)

    report = render_check(
        processed,
        kit_dist=kit_dist,
        public_origin=public_origin,
        interaction_seconds=interaction_seconds,
        plan_models=plan_models,
        kit_lane=lane != "free",
    )
    refusal = report.refusal()
    if refusal is not None:
        raise VerificationFailed("render", refusal[0], refusal[1])

    sha = html_sha256(processed)
    return _issue(
        env_id=env_id_for(slug, sha),
        title=title,
        lane=lane,
        label=label,
        kit_version=kit_version,
        kit_sha256=kit_sha,
        html=processed,
        html_sha256=sha,
        citations=cited,
        plan_summary=plan_summary,
        checked=Checked(
            layers=("postprocess", "scan", "render", "provenance", "grid", "reference")
            if lane != "free"
            else ("postprocess", "scan", "render"),
            controls_exercised=len(report.controls),
            readouts=report.readouts,
            grid_points=report.grid_points,
            reference_cases=report.reference_cases,
            models=tuple(report.models),
            interaction_seconds=round(report.interaction_seconds, 1),
        ),
    )
