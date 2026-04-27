from __future__ import annotations

from warehouse.duckdb_store import warehouse


class ReplayQueries:

    def latest_runtime_events(self, limit: int = 100):

        warehouse._ensure()

        rows = warehouse._conn.execute(
            """
            SELECT replay_hash,
                   event_type,
                   payload,
                   ts
            FROM runtime_events
            ORDER BY ts DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()

        return rows

    def top_hooks(self, limit: int = 20):

        warehouse._ensure()

        rows = warehouse._conn.execute(
            """
            SELECT hook,
                   AVG(actual_score) AS avg_score,
                   COUNT(*) AS n
            FROM learning_rows
            GROUP BY hook
            ORDER BY avg_score DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()

        return rows

    def top_angles(self, limit: int = 20):

        warehouse._ensure()

        rows = warehouse._conn.execute(
            """
            SELECT angle,
                   AVG(actual_score) AS avg_score,
                   COUNT(*) AS n
            FROM learning_rows
            GROUP BY angle
            ORDER BY avg_score DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()

        return rows


replay_queries = ReplayQueries()
