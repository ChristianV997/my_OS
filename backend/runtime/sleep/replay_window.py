"""replay_window — extract bounded event windows for a consolidation pass.

Reads from RuntimeReplayStore (durable) with EpisodicStore (in-process) as
secondary.  Returns a ReplayBatch containing all events in the requested
time window so the ConsolidationEngine works from a fixed snapshot.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from .schemas.replay_batch import ReplayBatch


def _replay_store():
    try:
        from backend.runtime.replay_store import get_replay_store
        return get_replay_store()
    except Exception:
        return None


def _episodic_store():
    try:
        from backend.memory.episodic import get_episodic_store
        return get_episodic_store()
    except Exception:
        return None


def extract_window(
    window_hours: float = 24.0,
    workspace: str = "default",
    max_events: int = 2000,
) -> ReplayBatch:
    """Extract the last *window_hours* of events from the durable replay store.

    Falls back to EpisodicStore if RuntimeReplayStore is unavailable.
    """
    end_ts   = time.time()
    start_ts = end_ts - window_hours * 3600.0
    events   = _extract_from_replay_store(start_ts, end_ts, max_events)
    source   = "replay_store"

    if not events:
        events = _extract_from_episodic(start_ts, end_ts)
        source = "episodic"

    return ReplayBatch(
        batch_id=uuid.uuid4().hex[:12],
        workspace=workspace,
        start_ts=start_ts,
        end_ts=end_ts,
        events=events[:max_events],
        source=source,
    )


def extract_recent(n: int = 500, workspace: str = "default") -> ReplayBatch:
    """Extract the last *n* events regardless of time window."""
    store = _replay_store()
    events: list[dict[str, Any]] = []
    if store:
        try:
            events = store.recent(n)
        except Exception:
            pass
    if not events:
        ep = _episodic_store()
        if ep:
            events = [e.to_dict() for e in ep.tail(n)]

    ts_vals = [float(e.get("ts", 0)) for e in events]
    start_ts = min(ts_vals) if ts_vals else time.time()
    end_ts   = max(ts_vals) if ts_vals else time.time()

    return ReplayBatch(
        batch_id=uuid.uuid4().hex[:12],
        workspace=workspace,
        start_ts=start_ts,
        end_ts=end_ts,
        events=events,
        source="replay_store",
    )


# ── internals ─────────────────────────────────────────────────────────────────


def _extract_from_replay_store(
    start_ts: float, end_ts: float, max_events: int
) -> list[dict[str, Any]]:
    store = _replay_store()
    if store is None:
        return []
    try:
        return store.since(start_ts, limit=max_events)
    except Exception:
        try:
            rows = store.recent(max_events)
            return [r for r in rows if start_ts <= float(r.get("ts", 0)) <= end_ts]
        except Exception:
            return []


def _extract_from_episodic(
    start_ts: float, end_ts: float
) -> list[dict[str, Any]]:
    ep = _episodic_store()
    if ep is None:
        return []
    try:
        episodes = ep.window(start_ts, end_ts)
        return [e.to_dict() for e in episodes]
    except Exception:
        return []
