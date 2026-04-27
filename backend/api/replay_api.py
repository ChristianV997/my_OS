from __future__ import annotations

from warehouse.replay_queries import replay_queries


class ReplayAPI:

    def latest_events(
        self,
        limit: int = 100,
    ):

        rows = replay_queries.latest_runtime_events(
            limit=limit,
        )

        return {
            "events": rows,
            "count": len(rows),
        }

    def top_hooks(
        self,
        limit: int = 10,
    ):

        rows = replay_queries.top_hooks(
            limit=limit,
        )

        return {
            "hooks": rows,
            "count": len(rows),
        }

    def top_angles(
        self,
        limit: int = 10,
    ):

        rows = replay_queries.top_angles(
            limit=limit,
        )

        return {
            "angles": rows,
            "count": len(rows),
        }


replay_api = ReplayAPI()
