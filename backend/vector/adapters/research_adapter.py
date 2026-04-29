"""ResearchAdapter — bridges ScienceR-Dsim artifacts into vector layer."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class ResearchAdapter:
    """Indexes simulation artifacts and research outputs as signals."""

    def __init__(self, signal_memory=None) -> None:
        if signal_memory is None:
            from ..memory.signal_memory import SignalMemory
            signal_memory = SignalMemory()
        self._sm = signal_memory

    def index_simulation_artifact(self, artifact: dict[str, Any]) -> int:
        """Index a simulation result dict as a market signal."""
        keyword = artifact.get("label") or artifact.get("name") or ""
        if not keyword:
            return 0
        return self._sm.index_keyword(
            keyword,
            artifact_type="simulation",
            source_repo="ScienceR-Dsim",
            **{k: v for k, v in artifact.items()
               if k not in ("label", "name") and isinstance(v, (str, int, float, bool))},
        )

    def index_batch_artifacts(self, artifacts: list[dict[str, Any]]) -> int:
        total = 0
        for a in artifacts:
            total += self.index_simulation_artifact(a)
        return total
