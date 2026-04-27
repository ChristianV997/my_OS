from __future__ import annotations

import hashlib
import json
from typing import Any


class DeterministicTelemetryOrdering:

    def normalize(
        self,
        telemetry_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        normalized = []

        for event in telemetry_events:

            canonical = {
                "campaign_id": event.get("campaign_id"),
                "product_name": event.get("product_name"),
                "hook": event.get("hook"),
                "angle": event.get("angle"),
                "type": event.get("type"),
                "ts": event.get("ts"),
            }

            replay_hash = hashlib.sha256(
                json.dumps(
                    canonical,
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()

            normalized.append({
                **event,
                "replay_hash": replay_hash,
            })

        normalized.sort(
            key=lambda e: (
                e.get("ts", 0),
                e.get("replay_hash", ""),
            )
        )

        return normalized


telemetry_ordering = DeterministicTelemetryOrdering()
