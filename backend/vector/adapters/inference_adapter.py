"""backend.vector.adapters.inference_adapter — inference → vector bridge.

Provides helpers to produce vector records from inference request /
response pairs, enabling semantic retrieval over inference history.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_TRACES
from backend.vector.indexing import index_record
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def index_inference_trace(
    request_id: str,
    prompt: str,
    response_text: str = "",
    model: str = "",
    provider: str = "",
    latency_ms: float = 0.0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> VectorRecord | None:
    """Index an inference request/response pair as a trace vector.

    The text indexed is the prompt (plus first 200 chars of response
    if available) so semantic retrieval surfaces relevant past prompts.

    Parameters
    ----------
    request_id    — inference request ID
    prompt        — prompt text
    response_text — model response text (optional; first 200 chars used)
    model         — model used
    provider      — provider used
    latency_ms    — inference latency
    """
    snippet = response_text[:200] if response_text else ""
    text = f"{prompt} {snippet}".strip()
    if not text:
        return None

    payload: dict[str, Any] = {
        "model": model,
        "provider": provider,
        "latency_ms": latency_ms,
        **(extra or {}),
    }
    return index_record(
        text=text,
        collection=COLLECTION_TRACES,
        source_id=request_id,
        source_type="inference_trace",
        payload=payload,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )
