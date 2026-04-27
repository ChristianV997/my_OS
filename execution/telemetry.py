from __future__ import annotations

import time
from typing import Any

from backend.pubsub.broker import broker
from warehouse.duckdb_store import warehouse


class ExecutionTelemetry:

    def record_campaign_launch(
        self,
        *,
        campaign_id: str,
        product_name: str,
        hook: str,
        angle: str,
        platform: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        payload = {
            "type": "campaign.launch",
            "campaign_id": campaign_id,
            "product_name": product_name,
            "hook": hook,
            "angle": angle,
            "platform": platform,
            "metadata": metadata or {},
            "ts": time.time(),
        }

        event_id = broker.publish(
            "campaign.launch",
            payload,
            source="execution",
        )

        warehouse.append_runtime_event(
            replay_hash=f"launch:{campaign_id}",
            event_type="campaign.launch",
            payload=payload,
            ts=payload["ts"],
        )

        return {
            "event_id": event_id,
            "campaign_id": campaign_id,
        }

    def record_campaign_metrics(
        self,
        *,
        campaign_id: str,
        product_name: str,
        hook: str,
        angle: str,
        metrics: dict[str, Any],
    ):

        payload = {
            "type": "campaign.metrics",
            "campaign_id": campaign_id,
            "product_name": product_name,
            "hook": hook,
            "angle": angle,
            "metrics": metrics,
            "ts": time.time(),
        }

        broker.publish(
            "campaign.metrics",
            payload,
            source="metrics",
        )

        warehouse.append_learning_row(
            campaign_id=campaign_id,
            product_name=product_name,
            hook=hook,
            angle=angle,
            predicted_score=float(metrics.get("predicted_score", 0)),
            actual_score=float(metrics.get("roas", 0)),
            metadata=metrics,
        )


execution_telemetry = ExecutionTelemetry()
