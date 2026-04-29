"""lineage_summarization — checkpoint and compact deep lineage branches.

When a lineage branch exceeds CompressionPolicy.max_lineage_depth, the
interior nodes are collapsed into a LineageSummary node.  The summary
preserves:
- root_node_id and tip_node_id for traceability
- all intermediate replay_hashes for deterministic re-expansion
- the workspace boundary (no cross-workspace collapse)
"""
from __future__ import annotations

import time
import uuid
import logging
from typing import Any

from .schemas.lineage_summary  import LineageSummary
from .policies.compression_policy import CompressionPolicy

log = logging.getLogger(__name__)


def _tracker():
    try:
        from backend.lineage import get_tracker
        return get_tracker()
    except Exception:
        return None


def summarize_deep_branches(
    workspace: str = "default",
    cycle_id: str = "",
    policy: CompressionPolicy | None = None,
) -> list[LineageSummary]:
    """Find branches deeper than policy.max_lineage_depth and summarize them.

    Returns the list of LineageSummary objects created.  Summaries are
    registered back into the LineageGraph as lightweight replacement nodes.
    """
    policy  = policy or CompressionPolicy()
    tracker = _tracker()
    if tracker is None:
        return []

    graph   = tracker.graph()
    nodes   = graph.nodes_by_workspace(workspace)
    summaries: list[LineageSummary] = []

    # Find root nodes (no parents in this workspace)
    ws_ids = {n.node_id for n in nodes}
    roots  = [n for n in nodes if not any(p in ws_ids for p in n.parent_ids)]

    for root in roots:
        chain   = graph.lineage_chain(root.node_id)
        if not policy.should_summarize_lineage(len(chain)):
            continue
        # Interior nodes = all except root and tip
        interior = chain[1:-1] if len(chain) > 2 else []
        if not interior:
            continue

        replay_hashes = []
        node_types    = []
        for nid in interior:
            node = graph.get(nid)
            if node:
                node_types.append(node.node_type)
                rh = node.payload.get("replay_hash", "")
                if rh:
                    replay_hashes.append(rh)

        summary = LineageSummary(
            summary_id=uuid.uuid4().hex[:12],
            workspace=workspace,
            root_node_id=chain[0],
            tip_node_id=chain[-1],
            collapsed_count=len(interior),
            node_types=list(set(node_types)),
            replay_hashes=replay_hashes,
            cycle_id=cycle_id,
            created_at=time.time(),
        )
        summaries.append(summary)

        # Register the summary as a lightweight lineage node
        try:
            tracker.track(
                node_type="lineage_summary",
                node_id=summary.summary_id,
                label=f"summary({len(interior)} nodes)",
                parent_ids=[chain[0]],
                workspace=workspace,
                source="lineage_summarization",
                payload=summary.to_dict(),
            )
        except Exception as exc:
            log.debug("summarize_deep_branches: tracker.track failed: %s", exc)

    return summaries


def checkpoint_lineage(
    workspace: str = "default",
    cycle_id: str = "",
) -> dict[str, Any]:
    """Write a lineage checkpoint event to the durable log."""
    tracker = _tracker()
    summary = {
        "workspace":   workspace,
        "cycle_id":    cycle_id,
        "node_count":  tracker.node_count() if tracker else 0,
        "worldlines":  tracker.worldline_count() if tracker else 0,
        "ts":          time.time(),
    }
    try:
        from backend.events.log import append
        append("lineage.checkpoint", payload=summary, source="lineage_summarization")
    except Exception:
        pass
    return summary
