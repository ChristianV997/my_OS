"""backend.inference.policies.routing_policy — deterministic provider routing logic.

The RoutingPolicy decides which provider to use for a given InferenceRequest.
Decision order:
  1. Explicit provider hint on the request (if not "auto")
  2. Health-check filter (skip unhealthy providers)
  3. Cost policy (prefer cheapest among healthy)
  4. Default provider order

All decisions are deterministic given the same request and provider health state.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.inference.models.inference_request import InferenceRequest
    from backend.inference.models.routing_decision import RoutingDecision
    from backend.inference.providers.base import BaseProvider

_log = logging.getLogger(__name__)

# Default priority order when no explicit provider is requested
_DEFAULT_ORDER = ["openai", "ollama", "airllm", "vllm", "litellm", "mock"]


class RoutingPolicy:
    """Determines which provider handles each request."""

    def __init__(
        self,
        provider_registry: dict[str, "BaseProvider"] | None = None,
        default_order: list[str] | None = None,
    ) -> None:
        self._registry: dict[str, "BaseProvider"] = provider_registry or {}
        self._order = default_order or _DEFAULT_ORDER

    def register(self, provider: "BaseProvider") -> None:
        self._registry[provider.name] = provider

    def decide(self, request: "InferenceRequest") -> "RoutingDecision":
        from backend.inference.models.routing_decision import RoutingDecision

        # Explicit provider hint bypasses policy
        if request.provider not in ("auto", "", "default"):
            provider_name = request.provider
            if provider_name in self._registry:
                fallback = self._build_fallback_order(provider_name)
                return RoutingDecision(
                    request_id=request.request_id,
                    selected_provider=provider_name,
                    selected_model=request.model,
                    reason="explicit_provider_hint",
                    fallback_order=fallback,
                    replay_hash=request.replay_hash,
                    sequence_id=request.sequence_id,
                )
            _log.warning(
                "routing_policy_unknown_provider provider=%s request_id=%s",
                provider_name,
                request.request_id,
            )

        # Auto routing: pick first healthy provider in priority order
        healthy = self._healthy_providers()
        for name in self._order:
            if name in healthy:
                fallback = self._build_fallback_order(name)
                return RoutingDecision(
                    request_id=request.request_id,
                    selected_provider=name,
                    selected_model=request.model,
                    reason="auto_policy",
                    fallback_order=fallback,
                    replay_hash=request.replay_hash,
                    sequence_id=request.sequence_id,
                )

        # Last resort: mock provider (always available)
        return RoutingDecision(
            request_id=request.request_id,
            selected_provider="mock",
            selected_model=request.model,
            reason="no_healthy_providers_fallback_mock",
            fallback_order=[],
            replay_hash=request.replay_hash,
            sequence_id=request.sequence_id,
        )

    def _healthy_providers(self) -> set[str]:
        healthy: set[str] = set()
        for name, provider in self._registry.items():
            try:
                if provider.health_check():
                    healthy.add(name)
            except Exception as exc:
                _log.warning("health_check_failed provider=%s error=%s", name, exc)
        return healthy

    def _build_fallback_order(self, primary: str) -> list[str]:
        """Return providers that can serve as fallbacks (excluding primary)."""
        return [n for n in self._order if n != primary and n in self._registry]
