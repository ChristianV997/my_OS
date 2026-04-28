"""backend.vector.adapters.replay_adapter — replay events → vector index.

Reads events from RuntimeReplayStore (via the DuckDB warehouse) and
indexes their payloads into the telemetry collection for semantic
retrieval over historical runtime state.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_TELEMETRY
from backend.vector.indexing import index_batch
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def _event_to_text(event: dict[str, Any]) -> str:
    """Produce a searchable text representation of a runtime event."""
    parts = []
    event_type = event.get("event_type") or event.get("type", "")
    if event_type:
        parts.append(event_type)
    payload = event.get("payload") or {}
    if isinstance(payload, dict):
        for key in ("phase", "worker", "product", "hook", "angle", "source", "message"):
            val = payload.get(key)
            if val:
                parts.append(str(val))
    return " ".join(parts).strip()


def index_replay_events(events: list[dict[str, Any]]) -> int:
    """Index a list of replay event dicts into the telemetry collection.

    Each event is expected to have:
      - "replay_hash"  : str
      - "event_type"   : str
      - "payload"      : dict
      - "ts"           : float
    """
    items = []
    for ev in events:
        text = _event_to_text(ev)
        if not text:
            continue
        items.append({
            "text": text,
            "source_id": ev.get("replay_hash") or ev.get("event_type", ""),
            "payload": {
                "event_type": ev.get("event_type", ""),
                "ts": ev.get("ts", 0.0),
            },
            "replay_hash": ev.get("replay_hash"),
            "sequence_id": ev.get("sequence_id"),
        })
    return index_batch(items, collection=COLLECTION_TELEMETRY, source_type="telemetry")
