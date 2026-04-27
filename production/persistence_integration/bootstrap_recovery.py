from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from production.persistence_backends.event_archive import (
    event_archive,
)

from production.persistence_backends.runtime_snapshots import (
    runtime_snapshot_store,
)

from production.replay.replay_engine import (
    runtime_replay_engine,
)


@dataclass(slots=True)
class BootstrapRecoveryResult:
    restored: bool
    replayed_events: int
    snapshot_count: int
    metadata: Dict


class BootstrapRecovery:
    """
    Replay-backed runtime recovery boot.
    """

    async def recover(self) -> BootstrapRecoveryResult:
        snapshots = (
            runtime_snapshot_store
            .load_all()
        )

        events = (
            event_archive
            .replay()
        )

        replayed = 0

        for event in events:
            await (
                runtime_replay_engine
                .replay_event(event)
            )

            replayed += 1

        return BootstrapRecoveryResult(
            restored=(
                len(snapshots) > 0
            ),
            replayed_events=replayed,
            snapshot_count=len(
                snapshots
            ),
            metadata={
                "latest_snapshot": (
                    snapshots[-1]
                    if snapshots
                    else None
                ),
            },
        )


bootstrap_recovery = (
    BootstrapRecovery()
)
