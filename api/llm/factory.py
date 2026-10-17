# Adapted from Azimlearning/Arcana-v2, api/llm/factory.py @ 21c6dcf5. Read in full. Change: live mode builds only the Anthropic
# provider (OpenRouter is not built), and only after the key, the cap and an absolute ledger path are all present.
"""Build the LLM service for the configured mode (SYNAPSE_LLM_MODE)."""

from __future__ import annotations

from collections.abc import Callable

from api.core.errors import ProviderUnavailable
from api.core.settings import ConfigError, Settings
from api.llm.ledger import SpendLedger, engine_for
from api.llm.providers.anthropic import AnthropicProvider
from api.llm.providers.fake import FakeProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest


def _require_live_prerequisites(settings: Settings) -> None:
    """Live mode never runs uncapped, whatever path built the Settings (load_settings checks too, but Settings can be constructed directly)."""
    missing = settings.missing_for_mode()
    if missing:
        raise ConfigError(missing)


def build_ledger(settings: Settings) -> SpendLedger:
    """The ledger at the configured path, capped by LLM_MONTHLY_CAP_USD (None: uncapped, which only fake mode allows)."""
    _require_live_prerequisites(settings)
    return SpendLedger(engine_for(settings.resolved_ledger_path()), settings.llm_monthly_cap_usd)


def build_llm_service(
    settings: Settings,
    ledger: SpendLedger,
    fake_responder: Callable[[LLMRequest], str] | None = None,
) -> LLMService:
    """Fake mode: one free fake provider. Live mode: the Anthropic provider behind the ledger and its cap, never uncapped."""
    if settings.synapse_llm_mode == "fake":
        if fake_responder is None:
            from api.pipeline.fakes import (
                fake_responder as pipeline_fakes,
            )  # purpose-aware fakes for the pipeline (route, plan, fill)

            fake_responder = pipeline_fakes
        provider = FakeProvider(fake_responder)
        return LLMService(provider, None, ledger)
    _require_live_prerequisites(settings)
    if settings.anthropic_api_key is None:
        raise ProviderUnavailable("Live mode needs ANTHROPIC_API_KEY; no provider was built.")
    # No OpenRouter fallback is built (CLAUDE.md names it optional): a failed call goes to the pipeline's degrade ladder instead.
    return LLMService(AnthropicProvider(settings.anthropic_api_key.get_secret_value()), None, ledger)
