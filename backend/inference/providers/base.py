"""backend.inference.providers.base — abstract base class for all inference providers."""
from __future__ import annotations

import abc
import time
from typing import AsyncIterator

from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.inference_response import InferenceResponse, TokenUsage
from backend.inference.models.embedding_request import EmbeddingRequest, EmbeddingResponse


class BaseProvider(abc.ABC):
    """Abstract base for all inference providers.

    Concrete providers must implement:
      - complete(request) → InferenceResponse
      - stream(request)   → AsyncIterator[str]   (token chunks)

    Embedding providers should also implement:
      - embed(request)    → EmbeddingResponse

    All methods must:
      - be deterministic given the same InferenceRequest.replay_hash
      - preserve request_id, sequence_id, replay_hash in the response
      - emit telemetry via the broker (done in router.py, not here)
      - raise only InferenceProviderError (wraps underlying exceptions)
    """

    #: Short identifier used in routing decisions and telemetry
    name: str = "base"

    #: Whether the provider supports token streaming
    supports_streaming: bool = False

    #: Whether the provider supports embedding generation
    supports_embeddings: bool = False

    @abc.abstractmethod
    def complete(self, request: InferenceRequest) -> InferenceResponse:
        """Run a synchronous completion and return the full response."""

    async def stream(
        self, request: InferenceRequest
    ) -> AsyncIterator[str]:  # pragma: no cover
        """Stream token chunks asynchronously.

        Default implementation calls complete() and yields the full text as one
        chunk.  Override for true streaming support.
        """
        response = self.complete(request)
        yield response.text

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings.  Override in providers that support embeddings."""
        return EmbeddingResponse(
            request_id=request.request_id,
            model=request.model,
            provider=self.name,
            sequence_id=request.sequence_id,
            replay_hash=request.replay_hash,
            error=f"Provider '{self.name}' does not support embeddings",
        )

    def health_check(self) -> bool:
        """Return True if the provider is currently reachable / available.

        Default is True (optimistic).  Override for real connectivity checks.
        """
        return True

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_response(
        request: InferenceRequest,
        text: str,
        provider: str,
        model: str | None = None,
        usage: TokenUsage | None = None,
        start_time: float | None = None,
        fallback_used: bool = False,
        fallback_chain: list[str] | None = None,
        **extra,
    ) -> InferenceResponse:
        latency_ms = (time.time() - start_time) * 1000.0 if start_time else 0.0
        return InferenceResponse(
            request_id=request.request_id,
            model=model or request.model,
            provider=provider,
            text=text,
            usage=usage or TokenUsage(),
            latency_ms=latency_ms,
            sequence_id=request.sequence_id,
            replay_hash=request.replay_hash,
            correlation_id=request.correlation_id,
            fallback_used=fallback_used,
            fallback_chain=fallback_chain or [],
            stream=request.stream,
            extra=extra,
        )

    @staticmethod
    def _make_error_response(
        request: InferenceRequest,
        provider: str,
        error: str,
        start_time: float | None = None,
    ) -> InferenceResponse:
        latency_ms = (time.time() - start_time) * 1000.0 if start_time else 0.0
        return InferenceResponse(
            request_id=request.request_id,
            model=request.model,
            provider=provider,
            text="",
            latency_ms=latency_ms,
            sequence_id=request.sequence_id,
            replay_hash=request.replay_hash,
            correlation_id=request.correlation_id,
            error=error,
        )


class InferenceProviderError(Exception):
    """Raised by providers when a completion or embedding call fails."""

    def __init__(self, provider: str, message: str):
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.message = message
