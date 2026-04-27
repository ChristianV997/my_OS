from __future__ import annotations

import random
import time
from typing import Any

from execution.telemetry import execution_telemetry
from metrics.attribution import attribution_registry


class TikTokAnalyticsProvider:

    def ingest_campaign(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:

        attribution = attribution_registry.resolve(
            campaign_id
        )

        if attribution is None:
            return {
                "status": "missing_attribution",
                "campaign_id": campaign_id,
            }

        metrics = {
            "views": random.randint(1000, 100000),
            "clicks": random.randint(100, 5000),
            "ctr": round(random.uniform(0.01, 0.12), 4),
            "roas": round(random.uniform(0.5, 4.5), 2),
            "watch_time": random.randint(3, 40),
            "shares": random.randint(0, 2000),
            "comments": random.randint(0, 500),
            "predicted_score": round(random.uniform(0.2, 1.0), 4),
            "ts": time.time(),
        }

        execution_telemetry.record_campaign_metrics(
            campaign_id=campaign_id,
            product_name=attribution.product_name,
            hook=attribution.hook,
            angle=attribution.angle,
            metrics=metrics,
        )

        return {
            "status": "ingested",
            "campaign_id": campaign_id,
            "metrics": metrics,
        }


analytics_provider = TikTokAnalyticsProvider()
