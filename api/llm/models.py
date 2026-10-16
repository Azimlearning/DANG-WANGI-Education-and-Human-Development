# Adapted from Azimlearning/Arcana-v2, api/llm/models.py @ 21c6dcf5. Read in full. Anthropic ids only until a live
# provider exists (P3); OpenRouter ids are not carried over because nothing uses them yet.
"""Model ids per provider and tier (heavy, standard, light).

ASSUMED: these ids and the prices in pricing.py are as recorded in refdocs/synapse-v4-sources.md. Confirm both against the
provider's current model and pricing pages before the first live call (the first paid run needs the owner's go anyway).
"""

from __future__ import annotations

from api.llm.types import Tier

ANTHROPIC_MODELS: dict[Tier, str] = {
    "heavy": "claude-opus-5-5",
    "standard": "claude-sonnet-5-5",
    "light": "claude-haiku-4-5",
}
