"""simulation.replay — DuckDB analytical replay for historical outcome queries.

Provides fast SQL-based aggregation over historical event rows, used to build
feature inputs and baseline statistics for the scoring model.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

_log = logging.getLogger(__name__)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS sim_events (
    ts          DOUBLE,
    product     VARCHAR,
    hook        VARCHAR,
    angle       VARCHAR,
    env_regime  VARCHAR,
    roas        DOUBLE,
    ctr         DOUBLE,
    cvr         DOUBLE,
    label       VARCHAR,
    eng_score   DOUBLE,
    platform    VARCHAR
);
"""


class ReplayStore:
    """In-process DuckDB store for historical event replay.

    Uses an in-memory database by default so it never touches disk.
    Thread-safe via a single lock (DuckDB connections are not thread-safe).
    """

    def __init__(self, db_path: str = ":memory:"):
        self._lock = threading.Lock()
        self._db_path = db_path
        self._conn = None  # lazy — initialized on first use
        self._insert_count = 0

    def _ensure_init(self) -> None:
        """Lazy init — called before first DB operation."""
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
            _log.warning("replay_store_init_failed error=%s fallback=list", exc)
            self._conn = None

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(self, rows: list[dict]) -> int:
        """Bulk-insert event rows. Returns count inserted."""
        if not rows:
            return 0
        self._ensure_init()
        if self._conn is None:
            return 0

        records = []
        for r in rows:
            records.append((
                float(r.get("ts", time.time())),
                str(r.get("product", "")),
                str(r.get("hook", "")),
                str(r.get("angle", "")),
                str(r.get("env_regime", "")),
                float(r.get("roas", 0) or 0),
                float(r.get("ctr", 0) or 0),
                float(r.get("cvr", 0) or 0),
                str(r.get("label", "NEUTRAL")),
                float(r.get("eng_score", 0) or 0),
                str(r.get("platform", "tiktok")),
            ))

        with self._lock:
            try:
                self._conn.executemany(
                    "INSERT INTO sim_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    records,
                )
                self._insert_count += len(records)
                return len(records)
            except Exception as exc:
                _log.warning("replay_store_ingest_failed error=%s", exc)
                return 0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def product_history(self, product: str, limit: int = 100) -> list[dict]:
        """Return recent event rows for a given product."""
        return self._query(
            "SELECT * FROM sim_events WHERE product = ? ORDER BY ts DESC LIMIT ?",
            [product, limit],
        )

    def hook_stats(self, top_n: int = 10) -> list[dict]:
        """Return avg roas/ctr grouped by hook."""
        return self._query(
            """
            SELECT hook,
                   COUNT(*) AS n,
                   AVG(roas) AS avg_roas,
                   AVG(ctr)  AS avg_ctr,
                   AVG(eng_score) AS avg_eng
            FROM sim_events
            WHERE hook != ''
            GROUP BY hook
            ORDER BY avg_eng DESC
            LIMIT ?
            """,
            [top_n],
        )

    def angle_stats(self, top_n: int = 10) -> list[dict]:
        """Return avg roas/ctr grouped by angle."""
        return self._query(
            """
            SELECT angle,
                   COUNT(*) AS n,
                   AVG(roas) AS avg_roas,
                   AVG(ctr)  AS avg_ctr,
                   AVG(eng_score) AS avg_eng
            FROM sim_events
            WHERE angle != ''
            GROUP BY angle
            ORDER BY avg_eng DESC
            LIMIT ?
            """,
            [top_n],
        )

    def winner_rate(self, product: str = "") -> dict:
        """Return winner/loser/neutral counts (optionally filtered by product)."""
        if product:
            rows = self._query(
                "SELECT label, COUNT(*) AS n FROM sim_events WHERE product = ? GROUP BY label",
                [product],
            )
        else:
            rows = self._query(
                "SELECT label, COUNT(*) AS n FROM sim_events GROUP BY label", []
            )
        counts = {r["label"]: r["n"] for r in rows}
        total = sum(counts.values()) or 1
        return {
            "winner": counts.get("WINNER", 0),
            "loser": counts.get("LOSER", 0),
            "neutral": counts.get("NEUTRAL", 0),
            "total": total,
            "win_rate": round(counts.get("WINNER", 0) / total, 4),
        }

    def recent(self, limit: int = 50) -> list[dict]:
        """Return the most recent event rows."""
        return self._query(
            "SELECT * FROM sim_events ORDER BY ts DESC LIMIT ?", [limit]
        )

    def row_count(self) -> int:
        rows = self._query("SELECT COUNT(*) AS n FROM sim_events", [])
        return rows[0]["n"] if rows else 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _query(self, sql: str, params: list) -> list[dict]:
        self._ensure_init()
        if self._conn is None:
            return []
        with self._lock:
            try:
                rel = self._conn.execute(sql, params)
                cols = [d[0] for d in rel.description]
                return [dict(zip(cols, row)) for row in rel.fetchall()]
            except Exception as exc:
                _log.warning("replay_store_query_failed sql=%r error=%s", sql[:60], exc)
                return []


# module-level singleton (in-memory, per process)
replay_store = ReplayStore()
