from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from production.persistence_integration.bootstrap_recovery import (
    bootstrap_recovery,
)

from runtime.integration.runtime_kernel import (
    runtime_kernel,
)


@dataclass(slots=True)
class ReplayBootResult:
    initialized: bool
    restored: bool
    metadata: Dict


class ReplayBoot:
    """
    Replay-backed runtime restoration boot.
    """

    async def boot(
        self,
    ) -> ReplayBootResult:
        recovery = await (
            bootstrap_recovery
            .recover()
        )

        kernel = await (
            runtime_kernel
            .initialize()
        )

        return ReplayBootResult(
            initialized=(
                kernel.initialized
            ),
            restored=(
                recovery.restored
            ),
            metadata={
                "replayed_events": (
                    recovery
                    .replayed_events
                ),
                "snapshots": (
                    recovery
                    .snapshot_count
                ),
            },
        )


replay_boot = ReplayBoot()
