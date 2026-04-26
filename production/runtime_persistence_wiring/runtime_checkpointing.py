from __future__ import annotations

import time

from dataclasses import dataclass
from typing import Dict

from backend.runtime.state import (
    RuntimeState,
)

from production.persistence_backends.runtime_snapshots import (
    runtime_snapshot_store,
)

from runtime.governance.policy_guardrails import (
    runtime_policy_guardrails,
)


@dataclass(slots=True)
class RuntimeCheckpoint:
    persisted: bool
    snapshot_id: str
    timestamp: float
    metadata: Dict


class RuntimeCheckpointing:
    """
    Automatic RuntimeState checkpoint persistence.
    """

    async def checkpoint(
        self,
        *,
        runtime_state: RuntimeState,
        correlation_id: str,
    ) -> RuntimeCheckpoint:
        governance = await (
            runtime_policy_guardrails
            .validate(runtime_state)
        )

        if not governance[
            "allowed"
        ]:
            return RuntimeCheckpoint(
                persisted=False,
                snapshot_id="blocked",
                timestamp=time.time(),
                metadata={
                    "reason": (
                        "governance"
                    ),
                },
            )

        snapshot = (
            runtime_snapshot_store
            .save(
                runtime_state=(
                    runtime_state
                ),
                metadata={
                    "correlation_id": (
                        correlation_id
                    ),
                    "checkpoint": True,
                },
            )
        )

        return RuntimeCheckpoint(
            persisted=True,
            snapshot_id=(
                snapshot.snapshot_id
            ),
            timestamp=time.time(),
            metadata={
                "correlation_id": (
                    correlation_id
                ),
            },
        )


runtime_checkpointing = (
    RuntimeCheckpointing()
)
