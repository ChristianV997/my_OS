"""backend.inference.streaming — WebSocket-compatible inference streaming.

Bridges the async generator returned by InferenceRouter.stream() with the
existing WebSocket event bus so that streaming tokens can be forwarded to
connected frontend clients without breaking replay safety.

Each streaming session:
  1. Emits inference.stream_start to the broker
  2. Accumulates tokens and optionally forwards them as inference.token events
  3. Emits inference.stream_end with full duration and token count

The module does NOT depend on a live WebSocket connection — it uses the
PubSubBroker so any connected consumer (WS, test listener, replay store)
receives the stream.

Usage (non-streaming callers)
------------------------------
    from backend.inference.streaming import stream_to_broker

    # Within an async context:
    full_text = await stream_to_broker(request)
"""
from __future__ import annotations

import logging
import time

from backend.inference.models.inference_request import InferenceRequest

_log = logging.getLogger(__name__)

# Event type for individual token chunks (not in the main event schema —
# high-frequency events are only streamed, not persisted to the replay store)
INFERENCE_TOKEN = "inference.token"


async def stream_to_broker(
    request: InferenceRequest,
    emit_tokens: bool = False,
) -> str:
    """Stream a completion and publish token events to the broker.

    Parameters
    ----------
    request : InferenceRequest
        The inference request to stream.
    emit_tokens : bool
        If True, each individual token chunk is published as an
        inference.token event.  Defaults to False to reduce broker volume.

    Returns
    -------
    str
        The fully assembled response text.
    """
    from backend.inference.router import inference_router
    from backend.inference.telemetry import emit_stream_start, emit_stream_end

    start = time.time()
    tokens: list[str] = []

    emit_stream_start(
        request_id=request.request_id,
        provider="streaming",
        model=request.model,
        replay_hash=request.replay_hash,
        sequence_id=request.sequence_id,
    )

    try:
        async for token in inference_router.stream(request):
            tokens.append(token)
            if emit_tokens:
                _emit_token(request, token, len(tokens))
    except Exception as exc:
        _log.warning("stream_to_broker_error request_id=%s error=%s", request.request_id, exc)

    full_text = "".join(tokens)
    duration_ms = (time.time() - start) * 1000.0

    emit_stream_end(
        request_id=request.request_id,
        provider="streaming",
        model=request.model,
        duration_ms=duration_ms,
        tokens_streamed=len(tokens),
        replay_hash=request.replay_hash,
        sequence_id=request.sequence_id,
    )

    return full_text


def _emit_token(
    request: InferenceRequest,
    token: str,
    index: int,
) -> None:
    """Publish a single token chunk to the broker (fire-and-forget)."""
    try:
        from backend.pubsub.broker import broker
        broker.publish(
            INFERENCE_TOKEN,
            {
                "type": INFERENCE_TOKEN,
                "request_id": request.request_id,
                "token": token,
                "index": index,
                "replay_hash": request.replay_hash,
                "sequence_id": request.sequence_id,
                "ts": time.time(),
            },
            source="inference.streaming",
        )
    except Exception as exc:
        _log.warning("emit_token_failed error=%s", exc)
