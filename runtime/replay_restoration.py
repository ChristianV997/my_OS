from __future__ import annotations

from backend.api.replay_api import replay_api


class RuntimeReplayRestoration:

    def restore_runtime_state(
        self,
        limit: int = 100,
    ):

        replay = replay_api.latest_events(
            limit=limit,
        )

        reconstructed = {
            "events": replay["events"],
            "event_count": replay["count"],
            "status": "restored",
        }

        return reconstructed


runtime_replay_restoration = RuntimeReplayRestoration()
