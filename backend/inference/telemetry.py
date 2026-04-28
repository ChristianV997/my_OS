"""Inference telemetry — emits inference events into the canonical event broker.

All inference calls emit an INFERENCE_COMPLETED or INFERENCE_FAILED event
through backend.pubsub.broker so they appear in:
  * the WebSocket telemetry stream (frontend)
  * the RuntimeReplayStore (deterministic replay)
  * structured logs (structlog)

Fail-silent: telemetry failures never propagate to callers.
"""
from __future__ import annotations

import logging
import time

import structlog

from .models.inference_request  import InferenceRequest
from .models.inference_response import InferenceResponse
from .models.routing_decision   import RoutingDecision

_log     = logging.getLogger(__name__)
_slog    = structlog.get_logger(__name__)


def emit_inference_completed(
    request:  InferenceRequest,
    response: InferenceResponse,
    decision: RoutingDecision,
) -> None:
    payload = {
        "sequence_id":       request.sequence_id,
        "replay_hash":       response.replay_hash,
        "provider":          response.provider,
        "model":             response.model,
        "latency_ms":        round(response.latency_ms, 3),
        "prompt_tokens":     response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "total_tokens":      response.total_tokens,
        "fallback_used":     response.fallback_used,
        "fallback_reason":   response.fallback_reason,
        "cached":            response.cached,
        "replayed":          response.replayed,
        "cost_estimate_usd": decision.cost_estimate_usd,
        "ts":                time.time(),
    }

    _slog.info(
        "inference_completed",
        **{k: v for k, v in payload.items() if v is not None},
    )

    _publish("inference.completed", payload)


def emit_inference_failed(
    request:       InferenceRequest,
    decision:      RoutingDecision,
    provider_name: str,
    error:         str,
) -> None:
    payload = {
        "sequence_id":   request.sequence_id,
        "replay_hash":   _safe_hash(request),
        "provider":      provider_name,
        "model":         request.model,
        "error":         error,
        "fallback_chain": decision.fallback_chain,
        "ts":            time.time(),
    }
    _slog.warning("inference_failed", **payload)
    _publish("inference.failed", payload)


def emit_embedding_completed(
    request:  "EmbeddingRequest",  # type: ignore[name-defined]  # avoid circular
    provider: str,
    dims:     int,
    count:    int,
    latency_ms: float,
) -> None:
    payload = {
        "sequence_id": request.sequence_id,
        "provider":    provider,
        "dims":        dims,
        "count":       count,
        "latency_ms":  round(latency_ms, 3),
        "ts":          time.time(),
    }
    _slog.info("embedding_completed", **payload)
    _publish("inference.embedding.completed", payload)


# ── internal ─────────────────────────────────────────────────────────────────

def _publish(event_type: str, payload: dict) -> None:
    try:
        from backend.pubsub.broker import get_broker
        broker = get_broker()
        broker.publish(event_type, payload)
    except Exception as exc:
        _log.debug("inference_telemetry_publish_failed type=%s error=%s", event_type, exc)


def _safe_hash(request: InferenceRequest) -> str:
    try:
        from ._utils import compute_replay_hash
        return compute_replay_hash(request)
    except Exception:
        return "unknown"
