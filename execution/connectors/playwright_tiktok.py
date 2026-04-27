from __future__ import annotations

import time
from typing import Any

from execution.telemetry import execution_telemetry
from metrics.attribution import attribution_registry


class PlaywrightTikTokConnector:

    def deploy(
        self,
        *,
        campaign_id: str,
        product_name: str,
        hook: str,
        angle: str,
        script: str,
        caption: str,
        video_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        attribution_registry.register(
            campaign_id=campaign_id,
            product_name=product_name,
            hook=hook,
            angle=angle,
            platform="tiktok",
        )

        deployment_payload = {
            "campaign_id": campaign_id,
            "product_name": product_name,
            "hook": hook,
            "angle": angle,
            "script": script,
            "caption": caption,
            "video_path": video_path,
            "metadata": metadata or {},
            "platform": "tiktok",
            "ts": time.time(),
        }

        execution_telemetry.record_campaign_launch(
            campaign_id=campaign_id,
            product_name=product_name,
            hook=hook,
            angle=angle,
            platform="tiktok",
            metadata=deployment_payload,
        )

        return {
            "status": "deployment_prepared",
            "campaign_id": campaign_id,
            "platform": "tiktok",
        }


playwright_tiktok_connector = PlaywrightTikTokConnector()
