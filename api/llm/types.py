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
    cache_system: bool = False
    """Ask the provider to cache the system prompt. The service sets it, not a caller, and only when PROMPT_CACHING is on (off until a measured saving, B6)."""


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float | None = None
    """The provider's own cost figure when it reports one; otherwise the ledger estimates it."""
    cache_read_tokens: int = 0
    """Of `tokens_in`: the tokens served from the provider's cache, billed at a fraction of the base rate."""
    cache_write_tokens: int = 0
    """Of `tokens_in`: the tokens written to the provider's cache, billed at more than the base rate."""


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    fell_back: bool
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
