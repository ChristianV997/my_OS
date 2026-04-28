"""RoutingPolicy — selects provider + model for a given InferenceRequest.

Selection logic:
  1. Read ordered chain from FallbackPolicy (env override respected).
  2. Filter to providers registered in the router's provider map.
  3. Skip providers that are unavailable or over the cost cap.
  4. First surviving provider wins.
  5. Mock is appended as an unconditional last resort.
"""
from __future__ import annotations

import logging

from ..models.inference_request import InferenceRequest
from ..models.routing_decision import RoutingDecision
from ..providers.base import BaseProvider
from .cost_policy import CostPolicy
from .fallback_policy import FallbackPolicy

_log = logging.getLogger(__name__)


class RoutingPolicy:
    def __init__(
        self,
        fallback: FallbackPolicy | None = None,
        cost:     CostPolicy    | None = None,
    ) -> None:
        self._fallback = fallback or FallbackPolicy()
        self._cost     = cost     or CostPolicy()

    def select(
        self,
        request:   InferenceRequest,
        providers: list[BaseProvider],
    ) -> RoutingDecision:
        """Return a RoutingDecision indicating which provider to try first and
        the full ordered fallback chain."""
        provider_map = {p.name: p for p in providers}
        chain        = self._fallback.with_guaranteed_mock()

        # Restrict chain to registered providers
        chain = [name for name in chain if name in provider_map]
        if not chain:
            chain = ["mock"]

        selected  = "mock"
        model     = "mock-1.0"
        reason    = "no_providers_available"

        for name in chain:
            p = provider_map.get(name)
            if p is None:
                continue
            if not p.is_available():
                _log.debug("provider_unavailable provider=%s", name)
                continue
            candidate_model = self._resolve_model(request, p)
            if not self._cost.is_affordable(name, candidate_model, request.max_tokens):
                _log.debug("provider_over_budget provider=%s model=%s", name, candidate_model)
                continue

            selected = name
            model    = candidate_model
            reason   = "first_available"
            break

        return RoutingDecision(
            sequence_id=request.sequence_id,
            selected_provider=selected,
            selected_model=model,
            reason=reason,
            fallback_chain=chain,
            cost_estimate_usd=self._cost.estimate(selected, model, request.max_tokens),
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_model(request: InferenceRequest, provider: BaseProvider) -> str:
        if request.model != "default":
            return request.model
        return getattr(provider, f"_{provider.name}_model", None) or \
               getattr(provider, "_model", None) or \
               "default"
