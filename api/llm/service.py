# Adapted from Azimlearning/Arcana-v2, api/llm/service.py @ 21c6dcf5. Read in full. Changes: the per-turn token budget is
# dropped (P3 re-introduces a budget when there is a planner), stdlib logging, this repo's errors.
"""The LLM seam. Nothing else in the codebase calls a provider (hard constraint 8).

complete() tries the primary, then the fallback, on any ProviderFailure. Before each attempt it reserves that attempt's
worst-case cost against the monthly cap; a refusal there happens before the provider is invoked. Every attempt, including
failed ones, is written to the spend ledger.
"""

from __future__ import annotations

import logging

from api.core.errors import BadRequest, ProviderUnavailable
from api.llm.ledger import SpendLedger
from api.llm.pricing import cost_usd, estimate_call_cost
from api.llm.providers.base import Provider, ProviderFailure
from api.llm.types import MAX_OUTPUT_TOKENS, LLMRequest, LLMResult

log = logging.getLogger(__name__)


class LLMService:
    def __init__(self, primary: Provider, fallback: Provider | None, ledger: SpendLedger):
        self._providers = [primary] + ([fallback] if fallback is not None else [])
        self._ledger = ledger

    def remaining_usd(self) -> float | None:
        """What the monthly cap still allows (None: no cap). For up-front checks before a big job."""
        return self._ledger.remaining_usd()

    async def complete(self, request: LLMRequest) -> LLMResult:
        if not 1 <= request.max_tokens <= MAX_OUTPUT_TOKENS:
            raise BadRequest(f"max_tokens must be between 1 and {MAX_OUTPUT_TOKENS}.")

        last_failure: ProviderFailure | None = None
        for index, provider in enumerate(self._providers):
            model = provider.model_for(request.tier)
            reservation = self._ledger.reserve(estimate_call_cost(provider.name, model, request))
            try:
                response = await provider.complete(request, model)
            except ProviderFailure as failure:
                self._ledger.settle(
                    reservation,
                    provider=provider.name,
                    model=model,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    purpose=request.purpose,
                    status="failed",
                )
                log.warning("provider_failed provider=%s reason=%s", provider.name, failure.reason)
                last_failure = failure
                continue
            except BaseException:
                # Cancellation or a bug: release the reservation, then let it propagate.
                self._ledger.settle(
                    reservation,
                    provider=provider.name,
                    model=model,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    purpose=request.purpose,
                    status="failed",
                )
                raise

            # Price by the model that was REQUESTED (an id this code chose and the table knows), never by the id echoed
            # back. A provider-reported cost is trusted only as a lower bound: book the larger of the two.
            estimated = cost_usd(provider.name, model, response.tokens_in, response.tokens_out)
            cost = estimated if response.cost_usd is None else max(response.cost_usd, estimated)
            self._ledger.settle(
                reservation,
                provider=provider.name,
                model=response.model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=cost,
                purpose=request.purpose,
            )
            return LLMResult(
                text=response.text,
                provider=provider.name,
                model=response.model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=cost,
                fell_back=index > 0,
            )

        raise ProviderUnavailable("No LLM provider could serve the request.") from last_failure
