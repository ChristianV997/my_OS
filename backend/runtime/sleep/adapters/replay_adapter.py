"""ReplayAdapter — read from durable replay store for sleep cycle input."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)


class ReplayAdapter:
    """Reads events from RuntimeReplayStore and wraps them in ReplayBatch."""

    def recent_batch(self, n: int = 500, workspace: str = "default"):
        from ..replay_window import extract_recent
        return extract_recent(n=n, workspace=workspace)

    def window_batch(self, window_hours: float = 24.0, workspace: str = "default"):
        from ..replay_window import extract_window
        return extract_window(window_hours=window_hours, workspace=workspace)

    def event_count(self) -> int:
        try:
            from backend.runtime.replay_store import get_replay_store
            return get_replay_store().count()
        except Exception:
            return 0

    def prune_before(self, ts: float) -> int:
        """Prune events older than *ts* from the durable store."""
        try:
            from backend.runtime.replay_store import get_replay_store
            return get_replay_store().prune_before(ts)
        except Exception as exc:
            log.warning("ReplayAdapter.prune_before failed: %s", exc)
            return 0

    def prune_older_than_days(self, days: float = 7.0) -> int:
        cutoff = time.time() - days * 86400.0
        return self.prune_before(cutoff)
