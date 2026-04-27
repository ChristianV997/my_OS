from __future__ import annotations

from warehouse.replay_queries import replay_queries


class PatternStoreOptimizer:

    def best_hooks(
        self,
        limit: int = 10,
    ):

        return replay_queries.top_hooks(
            limit=limit,
        )

    def best_angles(
        self,
        limit: int = 10,
    ):

        return replay_queries.top_angles(
            limit=limit,
        )


patternstore_optimizer = PatternStoreOptimizer()
