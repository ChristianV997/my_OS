"""backend.inference.telemetry — inference telemetry instrumentation.

All inference requests and responses are instrumented through this module.
Events are published to the existing PubSubBroker so they appear in:
  - the durable RuntimeReplayStore
  - the WebSocket event stream
  - the command center frontend

Event types emitted
--------------------
inference.request      — fired when a request is dispatched to a provider
inference.response     — fired when a response is received (success or error)
inference.fallback     — fired each time a provider fallback is triggered
inference.stream_start — fired when streaming begins
inference.stream_end   — fired when streaming completes
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.inference.models.inference_request import InferenceRequest
    from backend.inference.models.inference_response import InferenceResponse
    from backend.inference.models.routing_decision import RoutingDecision

_log = logging.getLogger(__name__)

# ── event type constants ──────────────────────────────────────────────────────

INFERENCE_REQUEST      = "inference.request"
INFERENCE_RESPONSE     = "inference.response"
INFERENCE_FALLBACK     = "inference.fallback"
INFERENCE_STREAM_START = "inference.stream_start"
INFERENCE_STREAM_END   = "inference.stream_end"
INFERENCE_EMBED        = "inference.embed"


def _broker():
    try:
        from backend.pubsub.broker import broker as _b
        return _b
    except Exception:
        return None


def emit_inference_request(
    request: "InferenceRequest",
    decision: "RoutingDecision",
) -> None:
    """Emit an inference.request event when a provider is about to be called."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            INFERENCE_REQUEST,
            {
                "type": INFERENCE_REQUEST,
                "request_id": request.request_id,
                "model": request.model,
                "provider": decision.selected_provider,
                "sequence_id": request.sequence_id,
                "replay_hash": request.replay_hash,
                "correlation_id": request.correlation_id,
                "stream": request.stream,
                "ts": time.time(),
            },
            source="inference.router",
        )
    except Exception as exc:
        _log.warning("emit_inference_request_failed error=%s", exc)


def emit_inference_response(response: "InferenceResponse") -> None:
    """Emit an inference.response event with full telemetry payload."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            INFERENCE_RESPONSE,
            {
                "type": INFERENCE_RESPONSE,
                "request_id": response.request_id,
                "model": response.model,
                "provider": response.provider,
                "latency_ms": response.latency_ms,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "fallback_used": response.fallback_used,
                "fallback_chain": response.fallback_chain,
                "stream": response.stream,
                "error": response.error,
                "sequence_id": response.sequence_id,
                "replay_hash": response.replay_hash,
                "ts": response.ts,
            },
            source="inference.router",
        )
    except Exception as exc:
        _log.warning("emit_inference_response_failed error=%s", exc)


def emit_inference_fallback(
    request_id: str,
    failed_provider: str,
    next_provider: str,
    error: str,
    attempt: int,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> None:
    """Emit an inference.fallback event when a provider fails and the next is tried."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            INFERENCE_FALLBACK,
            {
                "type": INFERENCE_FALLBACK,
                "request_id": request_id,
                "failed_provider": failed_provider,
                "next_provider": next_provider,
                "error": error,
                "attempt": attempt,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="inference.router",
        )
    except Exception as exc:
        _log.warning("emit_inference_fallback_failed error=%s", exc)


def emit_stream_start(
    request_id: str,
    provider: str,
    model: str,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> None:
    """Emit an inference.stream_start event when streaming begins."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            INFERENCE_STREAM_START,
            {
                "type": INFERENCE_STREAM_START,
                "request_id": request_id,
                "provider": provider,
                "model": model,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="inference.router",
        )
    except Exception as exc:
        _log.warning("emit_stream_start_failed error=%s", exc)


def emit_stream_end(
    request_id: str,
    provider: str,
    model: str,
    duration_ms: float,
    tokens_streamed: int = 0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> None:
    """Emit an inference.stream_end event when streaming completes."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            INFERENCE_STREAM_END,
            {
                "type": INFERENCE_STREAM_END,
                "request_id": request_id,
                "provider": provider,
                "model": model,
                "duration_ms": duration_ms,
                "tokens_streamed": tokens_streamed,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="inference.router",
        )
    except Exception as exc:
        _log.warning("emit_stream_end_failed error=%s", exc)


def emit_embed(
    request_id: str,
    provider: str,
    model: str,
    text_count: int,
    latency_ms: float,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
    error: str | None = None,
) -> None:
    """Emit an inference.embed event after an embedding call."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            INFERENCE_EMBED,
            {
                "type": INFERENCE_EMBED,
                "request_id": request_id,
                "provider": provider,
                "model": model,
                "text_count": text_count,
                "latency_ms": latency_ms,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "error": error,
                "ts": time.time(),
            },
            source="inference.router",
        )
    except Exception as exc:
        _log.warning("emit_embed_failed error=%s", exc)
