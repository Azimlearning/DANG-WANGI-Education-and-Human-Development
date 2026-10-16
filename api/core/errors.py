# Adapted from Azimlearning/Arcana-v2, api/core/errors.py @ 21c6dcf5. Read in full. Changes: this repo's error codes
# (see packages/schema/src/errors.ts) and generated module path.
"""The one error shape. Every failure the client can see leaves as an ErrorEnvelope.

ErrorEnvelope, FieldIssue and ErrorCode are generated from packages/schema (api/schema/generated.py); this module only
builds them. An unexpected exception becomes a generic "internal" envelope: the detail goes to the log, never the client.
"""

from __future__ import annotations

from collections.abc import Sequence

from api.schema.generated import ErrorCode, ErrorEnvelope, FieldIssue


class SynapseError(Exception):
    code: ErrorCode = "internal"
    retryable: bool = False

    def __init__(self, message: str, issues: Sequence[FieldIssue] = ()):
        super().__init__(message)
        self.message = message
        self.issues = list(issues)

    def to_envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(code=self.code, message=self.message, issues=self.issues, retryable=self.retryable)


class ValidationFailed(SynapseError):
    code = "validation_failed"


class BadRequest(SynapseError):
    code = "bad_request"


class NotFound(SynapseError):
    code = "not_found"


class SpendCapExceeded(SynapseError):
    """The monthly LLM cap would be exceeded; refused before the call was sent."""

    code = "spend_cap_exceeded"


class ProviderUnavailable(SynapseError):
    code = "provider_unavailable"
    retryable = True


class ProviderRejected(SynapseError):
    """The provider refused for a reason a retry cannot fix (its balance, its key, our request). This is NOT the spend cap; the message says so."""

    code = "provider_unavailable"
    retryable = False


class VerificationRefused(SynapseError):
    """An Environment failed a verification layer. `issues` names the layer and the reason."""

    code = "verification_refused"


def envelope_from_exception(exc: BaseException) -> ErrorEnvelope:
    """Map any exception to the wire envelope without leaking internals."""
    if isinstance(exc, SynapseError):
        return exc.to_envelope()
    return ErrorEnvelope(code="internal", message="An internal error occurred.", issues=[], retryable=False)


# Transport mapping for non-stream endpoints. In a stream the envelope itself carries the failure.
HTTP_STATUS: dict[str, int] = {
    "validation_failed": 422,
    "bad_request": 400,
    "not_found": 404,
    "spend_cap_exceeded": 402,
    "provider_unavailable": 503,
    "verification_refused": 422,
    "internal": 500,
}
