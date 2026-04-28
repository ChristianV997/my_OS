"""backend.inference.router — centralized inference routing kernel.

ALL model calls should route through this module.  Never call provider
implementations directly from other parts of the codebase.

Architecture
------------
InferenceRouter
  - Holds a registry of BaseProvider instances
  - Uses RoutingPolicy to select the primary provider
  - Uses FallbackPolicy to decide when to retry with the next provider
  - Emits telemetry events for every request/response/fallback via telemetry.py
  - Preserves sequence_id, replay_hash, and correlation_id throughout

Usage
-----
    from backend.inference.router import inference_router

    request = InferenceRequest(prompt="Hello", model="gpt-4o-mini", provider="openai")
    response = inference_router.complete(request)
    print(response.text)

The module-level ``inference_router`` singleton is pre-configured with all
supported providers.  Providers that are unavailable (missing deps, no API key)
degrade gracefully — the fallback chain takes over automatically.
"""
from __future__ import annotations

import logging
import time
from typing import AsyncIterator

from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.inference_response import InferenceResponse
from backend.inference.models.embedding_request import EmbeddingRequest, EmbeddingResponse
from backend.inference.policies.fallback_policy import FallbackPolicy
from backend.inference.policies.routing_policy import RoutingPolicy
from backend.inference.providers.base import BaseProvider

_log = logging.getLogger(__name__)


class InferenceRouter:
    """Centralized inference router with fallback and telemetry."""

    def __init__(
        self,
        routing_policy: RoutingPolicy | None = None,
        fallback_policy: FallbackPolicy | None = None,
    ) -> None:
        self._routing_policy = routing_policy or RoutingPolicy()
        self._fallback_policy = fallback_policy or FallbackPolicy()

    # ── provider registration ─────────────────────────────────────────────────

    def register(self, provider: BaseProvider) -> None:
        """Register a provider with the router and routing policy."""
        self._routing_policy.register(provider)
        _log.debug("inference_router_registered provider=%s", provider.name)

    def get_provider(self, name: str) -> BaseProvider | None:
        return self._routing_policy._registry.get(name)

    # ── completion ────────────────────────────────────────────────────────────

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        """Route a completion request through the provider chain.

        Telemetry is emitted for every attempt (including fallbacks).
        The returned response carries the full fallback chain in
        ``response.fallback_chain`` and ``response.fallback_used``.
        """
        from backend.inference.telemetry import (
            emit_inference_request,
            emit_inference_response,
            emit_inference_fallback,
        )

        decision = self._routing_policy.decide(request)
        emit_inference_request(request, decision)

        fallback_chain = [decision.selected_provider]
        remaining = list(decision.fallback_order)
        current_provider_name = decision.selected_provider
        last_response: InferenceResponse | None = None

        for attempt in range(self._fallback_policy.max_retries + 1):
            provider = self._routing_policy._registry.get(current_provider_name)
            if provider is None:
                # Provider not registered — skip to next
                if remaining:
                    next_provider = remaining.pop(0)
                    _log.warning(
                        "inference_router_provider_not_found provider=%s next=%s",
                        current_provider_name,
                        next_provider,
                    )
                    current_provider_name = next_provider
                    fallback_chain.append(current_provider_name)
                    continue
                break

            try:
                response = provider.complete(request)
            except Exception as exc:
                _log.warning(
                    "inference_router_provider_exception provider=%s error=%s",
                    current_provider_name,
                    exc,
                )
                response = provider._make_error_response(
                    request, current_provider_name, str(exc)
                )

            last_response = response

            if not self._fallback_policy.should_fallback(response, attempt):
                # Success — annotate and return
                response.fallback_used = len(fallback_chain) > 1
                response.fallback_chain = list(fallback_chain)
                emit_inference_response(response)
                return response

            # Fallback
            if not remaining:
                _log.warning(
                    "inference_router_all_fallbacks_exhausted request_id=%s",
                    request.request_id,
                )
                break

            next_provider = remaining.pop(0)
            emit_inference_fallback(
                request_id=request.request_id,
                failed_provider=current_provider_name,
                next_provider=next_provider,
                error=response.error or "unknown",
                attempt=attempt,
                replay_hash=request.replay_hash,
                sequence_id=request.sequence_id,
            )
            current_provider_name = next_provider
            fallback_chain.append(current_provider_name)

        # Return last response (may be an error)
        if last_response is not None:
            last_response.fallback_used = len(fallback_chain) > 1
            last_response.fallback_chain = list(fallback_chain)
            emit_inference_response(last_response)
            return last_response

        # Should not reach here, but return a safe error response
        err_response = InferenceResponse(
            request_id=request.request_id,
            provider="none",
            model=request.model,
            sequence_id=request.sequence_id,
            replay_hash=request.replay_hash,
            correlation_id=request.correlation_id,
            fallback_chain=list(fallback_chain),
            fallback_used=True,
            error="all_providers_exhausted",
        )
        emit_inference_response(err_response)
        return err_response

    # ── streaming ─────────────────────────────────────────────────────────────

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        """Stream tokens from the routed provider.

        Emits stream_start / stream_end telemetry events.
        Falls back to complete() if the selected provider does not support streaming.
        """
        from backend.inference.telemetry import emit_stream_start, emit_stream_end

        decision = self._routing_policy.decide(request)
        provider = self._routing_policy._registry.get(decision.selected_provider)

        if provider is None:
            yield "[stream_error: no provider available]"
            return

        stream_start = time.time()
        emit_stream_start(
            request_id=request.request_id,
            provider=provider.name,
            model=request.model,
            replay_hash=request.replay_hash,
            sequence_id=request.sequence_id,
        )

        tokens_streamed = 0
        try:
            async for token in provider.stream(request):
                tokens_streamed += 1
                yield token
        except Exception as exc:
            _log.warning("inference_router_stream_error provider=%s error=%s", provider.name, exc)
            yield f"[stream_error: {exc}]"
        finally:
            duration_ms = (time.time() - stream_start) * 1000.0
            emit_stream_end(
                request_id=request.request_id,
                provider=provider.name,
                model=request.model,
                duration_ms=duration_ms,
                tokens_streamed=tokens_streamed,
                replay_hash=request.replay_hash,
                sequence_id=request.sequence_id,
            )

    # ── embeddings ────────────────────────────────────────────────────────────

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Route an embedding request to the best available provider."""
        from backend.inference.telemetry import emit_embed

        # Find first registered provider that supports embeddings
        for name in self._routing_policy._order:
            provider = self._routing_policy._registry.get(name)
            if provider is None:
                continue
            if not provider.supports_embeddings:
                continue
            if not provider.health_check():
                continue

            response = provider.embed(request)
            emit_embed(
                request_id=request.request_id,
                provider=response.provider,
                model=response.model,
                text_count=len(request.texts),
                latency_ms=response.latency_ms,
                replay_hash=request.replay_hash,
                sequence_id=request.sequence_id,
                error=response.error,
            )
            return response

        # No provider available
        resp = EmbeddingResponse(
            request_id=request.request_id,
            provider="none",
            model=request.model,
            sequence_id=request.sequence_id,
            replay_hash=request.replay_hash,
            error="no_embedding_provider_available",
        )
        emit_embed(
            request_id=request.request_id,
            provider="none",
            model=request.model,
            text_count=len(request.texts),
            latency_ms=0.0,
            replay_hash=request.replay_hash,
            sequence_id=request.sequence_id,
            error=resp.error,
        )
        return resp


# ── module-level singleton ────────────────────────────────────────────────────

def _build_default_router() -> InferenceRouter:
    """Build and return the default inference router with all providers registered."""
    from backend.inference.providers.mock import MockProvider
    from backend.inference.providers.openai import OpenAIProvider
    from backend.inference.providers.ollama import OllamaProvider
    from backend.inference.providers.vllm import VLLMProvider
    from backend.inference.providers.airllm import AirLLMProvider
    from backend.inference.providers.litellm import LiteLLMProvider

    router = InferenceRouter()
    for provider in [
        MockProvider(),
        OpenAIProvider(),
        OllamaProvider(),
        VLLMProvider(),
        AirLLMProvider(),
        LiteLLMProvider(),
    ]:
        router.register(provider)

    return router


inference_router = _build_default_router()
