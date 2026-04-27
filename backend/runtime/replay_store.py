"""backend.runtime.replay_store — durable append-only event log.

Persists every published EventEnvelope to a DuckDB table so that:
  - WebSocket clients reconnecting after an orchestrator restart can still
    be hydrated with recent history (in-process ReplayBuffer is lost on restart).
  - Simulation backtesting queries can replay any window of past events.
  - Operational debugging can reconstruct exact runtime state at any timestamp.

The store is wired into broker.publish() as a side-effect; publishers never
call it directly.

Env vars
--------
RUNTIME_REPLAY_DB        — path for on-disk persistence (default: :memory:)
RUNTIME_REPLAY_MAX_ROWS  — cap on stored rows before pruning (default: 5000)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.pubsub.broker import EventEnvelope

_log = logging.getLogger(__name__)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_events (
    event_id       VARCHAR,
    type           VARCHAR NOT NULL,
    ts             DOUBLE  NOT NULL,
    source         VARCHAR,
    event_version  INTEGER DEFAULT 1,
    correlation_id VARCHAR,
    payload        TEXT
);
CREATE INDEX IF NOT EXISTS ix_runtime_events_ts   ON runtime_events (ts);
CREATE INDEX IF NOT EXISTS ix_runtime_events_type ON runtime_events (type);
"""

_MAX_ROWS    = int(os.getenv("RUNTIME_REPLAY_MAX_ROWS", "5000"))
_PRUNE_EVERY = 500   # check row count every N appends


class RuntimeReplayStore:
    """Append-only event log backed by DuckDB.

    Lazy-initialized: no DuckDB connection is created until the first
    append() call, so importing this module in tests is always safe.
    Thread-safe: all DB operations run under a single lock.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._lock    = threading.Lock()
        self._db_path = db_path
        self._conn    = None
        self._count   = 0

    # ------------------------------------------------------------------
    # Lazy init
    # ------------------------------------------------------------------

    def _ensure_init(self) -> None:
        if self._conn is not None:
            return
        self._init()

    def _init(self) -> None:
        try:
            import duckdb
            with self._lock:
                if self._conn is None:
                    self._conn = duckdb.connect(self._db_path)
                    self._conn.execute(_CREATE_SQL)
        except Exception as exc:
            _log.warning("runtime_replay_store_init_failed error=%s", exc)
            self._conn = None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def append(self, env: "EventEnvelope") -> None:
        """Persist one EventEnvelope.  Called by broker.publish()."""
        self._ensure_init()
        if self._conn is None:
            return
        try:
            payload_json = json.dumps(env.payload, default=str)
            corr_id  = getattr(env, "correlation_id", None)
            version  = getattr(env, "event_version", 1)
            with self._lock:
                self._conn.execute(
                    "INSERT INTO runtime_events VALUES (?,?,?,?,?,?,?)",
                    [env.event_id, env.type, env.ts,
                     env.source, version, corr_id, payload_json],
                )
                self._count += 1
            if self._count % _PRUNE_EVERY == 0:
                self._prune()
        except Exception as exc:
            _log.warning("runtime_replay_append_failed error=%s", exc)

    def _prune(self) -> None:
        """Delete oldest rows when over limit."""
        try:
            with self._lock:
                total = self._conn.execute(
                    "SELECT COUNT(*) FROM runtime_events"
                ).fetchone()[0]
                if total > _MAX_ROWS:
                    excess = total - _MAX_ROWS
                    self._conn.execute(
                        "DELETE FROM runtime_events WHERE rowid IN "
                        "(SELECT rowid FROM runtime_events ORDER BY ts ASC LIMIT ?)",
                        [excess],
                    )
                    self._count = _MAX_ROWS
        except Exception as exc:
            _log.warning("runtime_replay_prune_failed error=%s", exc)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def recent(self, n: int = 50, event_type: str | None = None) -> list[dict]:
        """Return the n most-recent events in chronological order (oldest first)."""
        self._ensure_init()
        if self._conn is None:
            return []
        try:
            if event_type:
                sql    = ("SELECT event_id,type,ts,source,event_version,correlation_id,payload "
                          "FROM runtime_events WHERE type=? ORDER BY ts DESC LIMIT ?")
                params = [event_type, n]
            else:
                sql    = ("SELECT event_id,type,ts,source,event_version,correlation_id,payload "
                          "FROM runtime_events ORDER BY ts DESC LIMIT ?")
                params = [n]
            with self._lock:
                rows = self._conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in reversed(rows)]
        except Exception as exc:
            _log.warning("runtime_replay_recent_failed error=%s", exc)
            return []

    def since(self, ts: float, event_type: str | None = None,
              limit: int = 200) -> list[dict]:
        """Return events at or after ``ts``, optionally filtered by type."""
        self._ensure_init()
        if self._conn is None:
            return []
        try:
            if event_type:
                sql    = ("SELECT event_id,type,ts,source,event_version,correlation_id,payload "
                          "FROM runtime_events WHERE ts>=? AND type=? ORDER BY ts ASC LIMIT ?")
                params = [ts, event_type, limit]
            else:
                sql    = ("SELECT event_id,type,ts,source,event_version,correlation_id,payload "
                          "FROM runtime_events WHERE ts>=? ORDER BY ts ASC LIMIT ?")
                params = [ts, limit]
            with self._lock:
                rows = self._conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as exc:
            _log.warning("runtime_replay_since_failed error=%s", exc)
            return []

    def count(self, event_type: str | None = None) -> int:
        """Return total stored event count, optionally filtered by type."""
        self._ensure_init()
        if self._conn is None:
            return 0
        try:
            if event_type:
                sql, params = ("SELECT COUNT(*) FROM runtime_events WHERE type=?",
                               [event_type])
            else:
                sql, params = "SELECT COUNT(*) FROM runtime_events", []
            with self._lock:
                return self._conn.execute(sql, params).fetchone()[0]
        except Exception:
            return 0

    def prune_before(self, ts: float) -> int:
        """Delete all events before ``ts``.  Returns count deleted."""
        self._ensure_init()
        if self._conn is None:
            return 0
        try:
            with self._lock:
                n = self._conn.execute(
                    "SELECT COUNT(*) FROM runtime_events WHERE ts<?", [ts]
                ).fetchone()[0]
                self._conn.execute("DELETE FROM runtime_events WHERE ts<?", [ts])
                self._count = max(0, self._count - n)
            return n
        except Exception as exc:
            _log.warning("runtime_replay_prune_before_failed error=%s", exc)
            return 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        event_id, type_, ts, source, version, corr_id, payload_json = row
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except Exception:
            payload = {}
        return {
            "event_id":       event_id,
            "type":           type_,
            "ts":             ts,
            "source":         source,
            "event_version":  version,
            "correlation_id": corr_id,
            "payload":        payload,
        }


# ── module-level singleton ─────────────────────────────────────────────────────
# db_path can be overridden via RUNTIME_REPLAY_DB env var for on-disk persistence
_db_path = os.getenv("RUNTIME_REPLAY_DB", ":memory:")
runtime_replay_store = RuntimeReplayStore(db_path=_db_path)
