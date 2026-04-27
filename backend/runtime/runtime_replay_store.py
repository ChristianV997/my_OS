from __future__ import annotations

from typing import Any

from warehouse.duckdb_store import warehouse


class RuntimeReplayStore:

    def append(self, envelope: Any):

        try:
            warehouse.append_runtime_event(
                replay_hash=getattr(envelope, "replay_hash", ""),
                event_type=getattr(envelope, "type", "unknown"),
                payload=getattr(envelope, "payload", {}),
                ts=float(getattr(envelope, "ts", 0.0)),
            )
        except Exception:
            pass


runtime_replay_store = RuntimeReplayStore()
