from __future__ import annotations

from typing import Any

from warehouse.duckdb_store import warehouse


class LearningPersistence:

    def persist_outcome(
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

        warehouse.append_learning_row(
            campaign_id=campaign_id,
            product_name=product_name,
            hook=hook,
            angle=angle,
            predicted_score=predicted_score,
            actual_score=actual_score,
            metadata=metadata or {},
        )


learning_persistence = LearningPersistence()
