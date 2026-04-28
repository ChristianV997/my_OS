"""MockProvider — deterministic stub for tests and cold-start CI environments."""
from __future__ import annotations

import hashlib
import math
import random
import time

from ..models.embedding_request import EmbeddingRequest
from ..models.inference_request import InferenceRequest
from ..models.inference_response import InferenceResponse
from .base import BaseProvider

_MOCK_COMPLETIONS = [
    "Based on current market signals, this product niche shows strong engagement potential.",
    "The hook pattern indicates high CTR. Consider scaling the social-proof angle.",
    "Market regime indicates growth phase. Prioritize high-velocity signal products.",
    "Creative performance data suggests urgency hooks outperform in the current cycle.",
    "Pattern analysis complete. Top hooks align with problem-solution angles.",
    "Signal velocity is accelerating. Recommend EXPLORE phase transition.",
    "Calibration confirms predicted ROAS within 0.15 MAE. Model is well-calibrated.",
    "Winner clustering reveals two distinct creative archetypes for this product.",
    "Anomaly detected: CTR spike +34% above baseline. Scale budget to capture momentum.",
    "Cold-start mitigation active: borrowing hook strategy from similar product cluster.",
]

_EMBED_DIM = 384


def _deterministic_hash(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def _mock_vector(text: str, normalize: bool = True) -> list[float]:
    """Deterministic pseudo-random unit vector derived from text hash."""
    seed = _deterministic_hash(text) % (2**32)
    rng = random.Random(seed)
    vec = [rng.gauss(0.0, 1.0) for _ in range(_EMBED_DIM)]
    if normalize:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
    return vec


class MockProvider(BaseProvider):
    """Always available.  Outputs are deterministic for a given prompt hash."""

    name = "mock"

    def is_available(self) -> bool:
        return True

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        from .._utils import compute_replay_hash as _h
        idx = _deterministic_hash(request.prompt) % len(_MOCK_COMPLETIONS)
        content = _MOCK_COMPLETIONS[idx]
        return InferenceResponse(
            content=content,
            provider="mock",
            model="mock-1.0",
            sequence_id=request.sequence_id,
            replay_hash=_h(request),
            latency_ms=0.1,
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(content.split()),
        )

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        return [_mock_vector(t, request.normalize) for t in request.texts]
