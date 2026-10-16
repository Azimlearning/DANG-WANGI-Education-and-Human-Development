# Adapted from Azimlearning/Arcana-v2, api/llm/factory.py @ 21c6dcf5. Read in full. Change: live providers are not built in
# P0 (they arrive in P3 behind the owner's confirmation), so live mode builds nothing and says so.
"""Build the LLM service for the configured mode (SYNAPSE_LLM_MODE)."""

from __future__ import annotations

from collections.abc import Callable

from api.core.errors import ProviderUnavailable
from api.core.settings import ConfigError, Settings
from api.llm.ledger import SpendLedger, engine_for
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
    """Fake mode: one free fake provider. Live mode: not built until P3."""
    if settings.synapse_llm_mode == "fake":
        if fake_responder is None:
            from api.pipeline.fakes import (
                fake_responder as pipeline_fakes,
            )  # purpose-aware fakes for the pipeline (route, plan, fill)

            fake_responder = pipeline_fakes
        provider = FakeProvider(fake_responder)
        return LLMService(provider, None, ledger)
    raise ProviderUnavailable("Live LLM providers are not built until P3. Set SYNAPSE_LLM_MODE=fake.")
