"""backend.vector.adapters.telemetry_adapter — telemetry events → vector index.

Subscribes to the PubSubBroker and asynchronously indexes vector-relevant
events (signals, decisions, creatives, campaigns) into the appropriate
collections.

This adapter is optional — the vector layer functions without it.
It is designed to be started once during application startup by calling
``start_telemetry_indexing()``.
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)

# Event types we want to auto-index into the vector layer
_INDEXABLE_EVENT_TYPES = frozenset({
    "signals.updated",
    "decision.logged",
    "campaign.launched",
    "simulation.completed",
})


def _handle_event(event_type: str, payload: dict[str, Any]) -> None:
    """Route a broker event into the appropriate vector collection."""
    try:
        if event_type == "signals.updated":
            signals = payload.get("signals") or []
            if signals:
                from backend.vector.memory.signal_memory import index_signals_batch
                index_signals_batch(signals)

        elif event_type == "decision.logged":
            product = payload.get("product", "")
            hook = payload.get("hook", "")
            angle = payload.get("angle", "")
            label = payload.get("label", "")
            text = " ".join(p for p in [product, hook, angle] if p).strip()
            if text:
                from backend.vector.memory.creative_memory import index_creative
                source_id = payload.get("request_id") or f"decision:{product}:{hook}"
                index_creative(
                    source_id=source_id,
                    text=text,
                    creative_type="hook",
                    product=product,
                    roas=payload.get("roas", 0.0),
                    label=label,
                )

        elif event_type == "campaign.launched":
            campaign_id = payload.get("campaign_id", "")
            product = payload.get("product", "")
            hook = payload.get("hook", "")
            angle = payload.get("angle", "")
            text = " ".join(p for p in [product, hook, angle] if p).strip()
            if text and campaign_id:
                from backend.vector.memory.campaign_memory import index_campaign
                index_campaign(
                    source_id=campaign_id,
                    text=text,
                    product=product,
                    phase=payload.get("phase", ""),
                )

        elif event_type == "simulation.completed":
            scores = payload.get("scores") or []
            for s in scores[:20]:  # cap batch size
                text = s.get("product") or s.get("signal", "")
                if text:
                    from backend.vector.memory.signal_memory import index_signal
                    index_signal(
                        source_id=f"sim:{text}",
                        text=text,
                        source="simulation",
                        velocity=float(s.get("score", 0.0)),
                    )
    except Exception as exc:
        _log.warning("telemetry_adapter_handle_failed type=%s error=%s", event_type, exc)


def start_telemetry_indexing() -> bool:
    """Subscribe to broker events and begin auto-indexing.

    Returns True if subscription succeeded, False otherwise.
    This is a best-effort registration — failure does not affect the
    rest of the runtime.
    """
    try:
        from backend.pubsub.broker import broker

        for event_type in _INDEXABLE_EVENT_TYPES:
            broker.subscribe(
                event_type,
                lambda payload, et=event_type: _handle_event(et, payload),
            )
        _log.info("telemetry_indexing_started event_types=%s", list(_INDEXABLE_EVENT_TYPES))
        return True
    except Exception as exc:
        _log.warning("telemetry_indexing_start_failed error=%s", exc)
        return False
