# Adapted from Azimlearning/Arcana-v2, api/llm/pricing.py @ 21c6dcf5. Read in full. Changes: embeddings dropped (A-9), the
# figures are marked ASSUMED because they come from refdocs/synapse-v4-sources.md and are unchecked against the pricing page.
"""Cost estimates, in USD, used to enforce the monthly cap before a call is sent.

ASSUMED: prices are per million tokens (input, output) as recorded in refdocs/synapse-v4-sources.md (Haiku 4.5 at $1 and
$5, Sonnet 5.5 at $2 and $10, Opus 5.5 at $4 and $20). Re-check against the provider's pricing page before the first
live call. Estimates are deliberately conservative: input tokens are over-counted and output is assumed to run to
max_tokens. An unknown model is priced as the dearest one, so a typo can only over-reserve.
"""

from __future__ import annotations

import math
import re

from api.llm.types import LLMRequest

PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

_FALLBACK_PRICE = max(PRICES_PER_MTOK.values())

FREE_PROVIDERS = frozenset({"fake"})

_DATE_SUFFIX = re.compile(r"-\d{8}$")


def _normalise(model: str) -> str:
    """An alias for a model id: no provider prefix, dots as dashes, no dated-snapshot suffix."""
    return _DATE_SUFFIX.sub("", model.removeprefix("anthropic/").replace(".", "-"))


def price_for(provider: str, model: str) -> tuple[float, float]:
    if provider in FREE_PROVIDERS:
        return (0.0, 0.0)
    return PRICES_PER_MTOK.get(_normalise(model), _FALLBACK_PRICE)


def estimate_input_tokens(request: LLMRequest) -> int:
    """About one token per 3 characters: higher than the usual ~4, so it errs toward refusing."""
    chars = len(request.prompt) + len(request.system or "")
    return math.ceil(chars / 3)


def cost_usd(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = price_for(provider, model)
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def estimate_call_cost(provider: str, model: str, request: LLMRequest) -> float:
    """Worst case: the estimated input plus an output that fills max_tokens."""
    return cost_usd(provider, model, estimate_input_tokens(request), request.max_tokens)
