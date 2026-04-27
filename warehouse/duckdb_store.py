from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class OperationalWarehouse:

    def __init__(
        self,
        db_path: str = "runtime/warehouse.duckdb",
    ):

        self.path = Path(db_path)
        self._lock = threading.Lock()
        self._conn = None

    def _ensure(self):
        if self._conn is not None:
            return

        import duckdb

        with self._lock:
            if self._conn is None:
                self._conn = duckdb.connect(str(self.path))
                self._bootstrap()

    def _bootstrap(self):

        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_events (
                replay_hash TEXT,
                event_type TEXT,
                payload TEXT,
                ts DOUBLE
            )
            """
        )

        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_rows (
                campaign_id TEXT,
                product_name TEXT,
                hook TEXT,
                angle TEXT,
                predicted_score DOUBLE,
                actual_score DOUBLE,
                metadata TEXT
            )
            """
        )

    def append_runtime_event(
        self,
        *,
        replay_hash: str,
        event_type: str,
        payload: dict[str, Any],
        ts: float,
    ):

        self._ensure()

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO runtime_events
                VALUES (?, ?, ?, ?)
                """,
                [
                    replay_hash,
                    event_type,
                    json.dumps(payload),
                    ts,
                ],
            )

    def append_learning_row(
        self,
        *,
        campaign_id: str,
        product_name: str,
        hook: str,
        angle: str,
        predicted_score: float,
        actual_score: float,
        metadata: dict[str, Any] | None = None,
    ):

        self._ensure()

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO learning_rows
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    campaign_id,
                    product_name,
                    hook,
                    angle,
                    predicted_score,
                    actual_score,
                    json.dumps(metadata or {}),
                ],
            )


warehouse = OperationalWarehouse()
