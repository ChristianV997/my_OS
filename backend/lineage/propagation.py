"""Lineage propagation helpers — stamp and carry lineage across artifact boundaries.

When one artifact produces another (simulation → campaign → outcome), the
child must inherit the parent's lineage chain.  These helpers make that
one-liner safe and consistent.
"""
from __future__ import annotations

from typing import Any


def inherit_lineage(
    parent_ids: list[str],
    extra_parents: list[str] | None = None,
) -> list[str]:
    """Return a deduplicated parent_id list combining parent and extra parents."""
    combined = list(parent_ids)
    for p in (extra_parents or []):
        if p not in combined:
            combined.append(p)
    return combined


def stamp_artifact_lineage(
    artifact: Any,
    parent_artifact: Any | None = None,
    extra_parent_ids: list[str] | None = None,
) -> None:
    """Mutate *artifact.parent_ids* to include the parent artifact's ID.

    Works with any BaseArtifact subclass.
    """
    if parent_artifact is not None:
        pid = getattr(parent_artifact, "artifact_id", None)
        if pid and pid not in artifact.parent_ids:
            artifact.parent_ids.append(pid)
    for extra in (extra_parent_ids or []):
        if extra not in artifact.parent_ids:
            artifact.parent_ids.append(extra)


def extract_lineage_metadata(artifact: Any) -> dict[str, Any]:
    """Return a minimal lineage dict for embedding in event payloads."""
    return {
        "artifact_id":   getattr(artifact, "artifact_id", ""),
        "artifact_type": getattr(artifact, "artifact_type", ""),
        "parent_ids":    getattr(artifact, "parent_ids", []),
        "workspace":     getattr(artifact, "workspace", "default"),
        "replay_hash":   getattr(artifact, "replay_hash", ""),
    }


def build_lineage_chain(artifacts: list[Any]) -> list[str]:
    """Ordered list of artifact_ids representing a transformation pipeline."""
    return [getattr(a, "artifact_id", "") for a in artifacts if a]
