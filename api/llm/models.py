# Adapted from Azimlearning/Arcana-v2, api/llm/models.py @ 21c6dcf5. Read in full. Anthropic ids only until a live
# provider exists (P3); OpenRouter ids are not carried over because nothing uses them yet.
"""Model ids per provider and tier (heavy, standard, light).

Ids and prices were checked against the provider's models and pricing pages on 2026-10-16 (see pricing.py). Re-check both before the first live
call: they change.
"""

from __future__ import annotations

from api.llm.types import Tier

ANTHROPIC_MODELS: dict[Tier, str] = {
    "heavy": "claude-opus-5-5",
    "standard": "claude-sonnet-5-5",
    "light": "claude-haiku-5-5",
}
