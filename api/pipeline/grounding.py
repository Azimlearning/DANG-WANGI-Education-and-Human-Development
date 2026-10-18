"""Which citations and which label a Plan has earned (hard constraint 4). One implementation, used by the live pipeline and by `eval/environments/build.py`.

`kit-verified` only when the Plan names citations, a corpus is configured, and EVERY citation proves against it and supports this Plan. Anything less is
`model-checked` with an UNVERIFIED citation that says which reason applies. It never raises and never repairs: an unprovable citation is a downgrade, and
the reason goes to the trace.
"""

from __future__ import annotations

from api.evidence.registry import CitationBook
from api.pipeline.plan import Plan
from api.schema.generated import Citation
from api.verify.mint import Evidence

UNVERIFIED_CITATION = Citation(source="UNVERIFIED (corpus not loaded until P2)", page=None, quote=None, verified=False)
# With a corpus loaded, "not loaded" would be false: this Environment simply has no textbook page checked for it.
UNCHECKED_CITATION = Citation(
    source="UNVERIFIED (no textbook page has been checked for this Environment)", page=None, quote=None, verified=False
)


def grounding(book: CitationBook | None, evidence: Evidence | None, plan: Plan) -> tuple[list[Citation], str, dict]:
    """(citations, label, why). `why["grounded"]` is True only for `kit-verified`; the rest of `why` is what the trace records."""
    if book is None or evidence is None:
        return [UNVERIFIED_CITATION], "model-checked", {"grounded": False, "why": "no corpus configured"}
    if not plan.citation_ids:
        return [UNCHECKED_CITATION], "model-checked", {"grounded": False, "why": "the plan names no citation"}
    result = book.resolve(plan.citation_ids, topic=plan.topic, models=[m.model for m in plan.models])
    if result.ok:
        return list(result.citations), "kit-verified", {"grounded": True, "citations": list(plan.citation_ids)}
    return (
        [UNCHECKED_CITATION],
        "model-checked",
        {"grounded": False, "why": "a citation did not prove", "problems": list(result.problems)},
    )
