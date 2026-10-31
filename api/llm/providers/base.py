# Adapted from Azimlearning/Arcana-v2, api/llm/providers/base.py @ 21c6dcf5. Read in full; unchanged in shape.
"""The provider interface. Providers translate every SDK failure into ProviderFailure."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol

from api.llm.types import LLMRequest, ProviderResponse, Tier

# transient: try the fallback. timeout: the call may have been billed. truncated: the reply hit max_tokens (billed). credit_exhausted and auth: the
# provider's balance or key is the problem, NOT the spend cap; retrying or falling back is wrong, so the whole run stops. bad_request: our request is wrong.
FailureKind = Literal["transient", "timeout", "truncated", "credit_exhausted", "auth", "bad_request"]


class ProviderFailure(Exception):
    """A provider could not serve the call (rate limit, timeout, outage, refusal, bad status).

    The service answers any ProviderFailure by trying the fallback. `reason` is short and safe to log: it never carries
    a key or a response body.
    """

    def __init__(
        self,
        provider: str,
        reason: str,
        kind: FailureKind = "transient",
        *,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ):
        super().__init__(f"{provider}: {reason}")
        self.provider = provider
        self.reason = reason
        self.kind = kind
        # Set only when the provider answered and reported usage for a reply it then rejected (cut off at max_tokens, empty, refused).
        # That reply was billed, output included, so the service books these counts instead of an input-only estimate.
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out


TextSink = Callable[[str], None]
"""Receives each piece of a reply's text as it is generated. Must not raise and must not block."""


class Provider(Protocol):
    name: str

    def model_for(self, tier: Tier) -> str: ...

    async def complete(self, request: LLMRequest, model: str, on_text: TextSink | None = None) -> ProviderResponse:
        """The whole reply. With `on_text`, the reply's text is also handed over piece by piece as it is generated (W19, D-79), for a reader to watch; the
        response returned at the end, its usage and every failure are exactly those of a call without it."""
        ...
