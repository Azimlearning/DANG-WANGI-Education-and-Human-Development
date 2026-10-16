# Adapted from Azimlearning/Arcana-v2, api/llm/providers/fake.py @ 21c6dcf5. Read in full. Change: the default reply is
# derived from a SHA-256 of the prompt, so the same prompt always yields the same text (deterministic fakes).
"""A deterministic provider for tests and SYNAPSE_LLM_MODE=fake. Spends nothing, opens no socket.

`responder` maps a request to the reply text so each caller can supply a purpose-specific fake. `name` and `models` can be
set to make the fake price like a real provider, which is how the cap tests exercise non-zero costs.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable

from api.llm.models import ANTHROPIC_MODELS
from api.llm.providers.base import ProviderFailure
from api.llm.types import LLMRequest, ProviderResponse, Tier

_SENTENCES = (
    "A spring stores energy when it is stretched.",
    "The extension grows in proportion to the load, up to a limit.",
    "Doubling the load doubles the extension while the spring stays within that limit.",
    "Past the elastic limit the spring no longer returns to its first length.",
    "Try moving the slider and watch the readout change.",
)


def hashed_reply(request: LLMRequest) -> str:
    """Pick sentences from a fixed list by a hash of the prompt: same prompt, same reply, no randomness."""
    digest = hashlib.sha256(f"{request.purpose}\x00{request.system or ''}\x00{request.prompt}".encode()).digest()
    count = 2 + digest[0] % 3
    start = digest[1] % len(_SENTENCES)
    picked = [_SENTENCES[(start + i) % len(_SENTENCES)] for i in range(count)]
    return f"[fake:{request.purpose}:{digest.hex()[:8]}] " + " ".join(picked)


class FakeProvider:
    def __init__(
        self,
        responder: Callable[[LLMRequest], str] = hashed_reply,
        *,
        name: str = "fake",
        models: dict[Tier, str] | None = None,
        fail_with: str | None = None,
    ):
        self.name = name
        self._responder = responder
        self._models = models or ANTHROPIC_MODELS
        self._fail_with = fail_with
        self.calls: list[LLMRequest] = []

    def model_for(self, tier: Tier) -> str:
        return self._models[tier]

    async def complete(self, request: LLMRequest, model: str) -> ProviderResponse:
        self.calls.append(request)
        if self._fail_with is not None:
            raise ProviderFailure(self.name, self._fail_with)
        text = self._responder(request)
        chars_in = len(request.prompt) + len(request.system or "")
        return ProviderResponse(
            text=text,
            model=model,
            tokens_in=math.ceil(chars_in / 4),
            tokens_out=math.ceil(len(text) / 4),
        )
