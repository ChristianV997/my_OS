"""backend.inference.providers.mock — deterministic mock provider for testing.

Always returns predictable responses based on the request's replay_hash.
No external calls.  Used in unit tests and dry-run mode.
"""
from __future__ import annotations

import time
from typing import AsyncIterator

from backend.inference.models.embedding_request import EmbeddingRequest, EmbeddingResponse
from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.inference_response import InferenceResponse, TokenUsage
from backend.inference.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Deterministic mock provider — no network calls."""

    name = "mock"
    supports_streaming = True
    supports_embeddings = True

    # ── completion ────────────────────────────────────────────────────────────

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        start = time.time()
        text = f"[mock] replay_hash={request.replay_hash} prompt_len={len(request.prompt)}"
        usage = TokenUsage(
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(text.split()),
            total_tokens=len(request.prompt.split()) + len(text.split()),
        )
        return self._make_response(
            request,
            text=text,
            provider=self.name,
            model=request.model,
            usage=usage,
            start_time=start,
        )

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        response = self.complete(request)
        for word in response.text.split():
            yield word + " "

    # ── embeddings ────────────────────────────────────────────────────────────

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.time()
        # Deterministic fake embeddings: each text → a 4-element vector derived
        # from its hash so the same input always produces the same vector.
        embeddings = []
        for text in request.texts:
            h = hash(text) & 0xFFFFFFFF
            vec = [
                ((h >> 0) & 0xFF) / 255.0,
                ((h >> 8) & 0xFF) / 255.0,
                ((h >> 16) & 0xFF) / 255.0,
                ((h >> 24) & 0xFF) / 255.0,
            ]
            embeddings.append(vec)

        latency_ms = (time.time() - start) * 1000.0
        return EmbeddingResponse(
            request_id=request.request_id,
            model=request.model or "mock",
            provider=self.name,
            embeddings=embeddings,
            latency_ms=latency_ms,
            sequence_id=request.sequence_id,
            replay_hash=request.replay_hash,
        )
