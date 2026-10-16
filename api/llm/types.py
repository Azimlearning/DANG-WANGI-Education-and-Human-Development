# Adapted from Azimlearning/Arcana-v2, api/llm/types.py @ 21c6dcf5. Read in full; unchanged in shape.
"""Request and result types for the LLM seam."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["heavy", "standard", "light"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]

# Above this the Anthropic SDK wants streaming to avoid HTTP timeouts; no P0 task needs more.
MAX_OUTPUT_TOKENS = 16_000


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    purpose: str
    """What the call is for ("explain", "plan", ...). Recorded in the spend ledger."""
    tier: Tier = "standard"
    system: str | None = None
    max_tokens: int = 1024
    effort: Effort | None = None
    """Thinking depth. Sent only to models that accept it."""


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float | None = None
    """The provider's own cost figure when it reports one; otherwise the ledger estimates it."""


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    fell_back: bool
