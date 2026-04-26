from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

from backend.runtime.state import (
    RuntimeState,
)


SNAPSHOT_DIR = Path(
    "backend/state/runtime_snapshots"
)


@dataclass(slots=True)
class RuntimeSnapshot:
    snapshot_id: str
    timestamp: float
    metadata: Dict


class RuntimeSnapshotStore:
    """
    Durable RuntimeState snapshot persistence.
    """

    def save(
        self,
        *,
        runtime_state: RuntimeState,
        metadata: Dict,
    ) -> RuntimeSnapshot:
        SNAPSHOT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        snapshot_id = (
            f"snapshot_{int(time.time())}"
        )

        snapshot = RuntimeSnapshot(
            snapshot_id=snapshot_id,
            timestamp=time.time(),
            metadata=metadata,
        )

        payload = {
            "snapshot": asdict(
                snapshot
            ),
            "runtime_state": (
                runtime_state
                .model_dump()
            ),
        }

        path = (
            SNAPSHOT_DIR
            / f"{snapshot_id}.json"
        )

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            )
        )

        return snapshot

    def load_all(
        self,
    ) -> List[Dict]:
        if not SNAPSHOT_DIR.exists():
            return []

        snapshots = []

        for path in sorted(
            SNAPSHOT_DIR.glob(
                "*.json"
            )
        ):
            snapshots.append(
                json.loads(
                    path.read_text()
                )
            )

        return snapshots


runtime_snapshot_store = (
    RuntimeSnapshotStore()
)
