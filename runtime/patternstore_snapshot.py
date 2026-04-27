from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from warehouse.patternstore_optimizer import patternstore_optimizer


class PatternStoreSnapshot:

    def __init__(
        self,
        path: str = "runtime/patternstore_snapshot.json",
    ):

        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def snapshot(self):

        payload = {
            "top_hooks": patternstore_optimizer.best_hooks(),
            "top_angles": patternstore_optimizer.best_angles(),
            "ts": time.time(),
        }

        self.path.write_text(
            json.dumps(payload, indent=2, default=str)
        )

        return payload

    def restore(self) -> dict[str, Any]:

        if not self.path.exists():
            return {
                "top_hooks": [],
                "top_angles": [],
            }

        return json.loads(
            self.path.read_text()
        )


patternstore_snapshot = PatternStoreSnapshot()
