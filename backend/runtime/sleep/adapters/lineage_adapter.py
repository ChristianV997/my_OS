"""LineageAdapter — read/write lineage tracker for the sleep runtime."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class LineageAdapter:
    """Reads lineage state and registers sleep-cycle artifacts as lineage nodes."""

    def record_cycle(self, cycle_id: str, workspace: str, parent_ids: list[str]) -> str:
        """Register a consolidation cycle as a lineage node."""
        try:
            from backend.lineage import get_tracker
            return get_tracker().track(
                node_type="sleep_cycle",
                label=f"cycle:{cycle_id}",
                parent_ids=parent_ids,
                workspace=workspace,
                source="consolidation_engine",
                payload={"cycle_id": cycle_id},
            )
        except Exception as exc:
            log.debug("LineageAdapter.record_cycle failed: %s", exc)
            return ""

    def deep_branch_ids(self, workspace: str, max_depth: int = 100) -> list[str]:
        """Return node IDs whose ancestry chain exceeds max_depth."""
        try:
            from backend.lineage import get_tracker
            tracker = get_tracker()
            graph   = tracker.graph()
            deep    = []
            for node in graph.nodes_by_workspace(workspace):
                chain = graph.lineage_chain(node.node_id)
                if len(chain) > max_depth:
                    deep.append(node.node_id)
            return deep
        except Exception:
            return []

    def graph_stats(self) -> dict[str, Any]:
        try:
            from backend.lineage import get_tracker
            tracker = get_tracker()
            return {
                "node_count":     tracker.node_count(),
                "worldline_count": tracker.worldline_count(),
            }
        except Exception:
            return {}
