"""ArtifactRegistry — in-memory artifact catalog with lineage tracking.

Provides a thread-safe append-only store of all typed artifacts produced
during a runtime session.  On restart the registry is rebuilt from the
durable event log (ReplayArtifact events).
"""
from __future__ import annotations

import threading
from typing import Any, Type

from .base        import BaseArtifact
from .simulation  import SimulationArtifact
from .research    import ResearchArtifact
from .workflow    import WorkflowArtifact
from .semantic    import SemanticAsset
from .campaign    import CampaignAsset
from .replay      import ReplayArtifact


_TYPE_MAP: dict[str, Type[BaseArtifact]] = {
    "simulation": SimulationArtifact,
    "research":   ResearchArtifact,
    "workflow":   WorkflowArtifact,
    "semantic":   SemanticAsset,
    "campaign":   CampaignAsset,
    "replay":     ReplayArtifact,
    "base":       BaseArtifact,
}


class ArtifactRegistry:
    """Thread-safe in-memory store of all produced artifacts."""

    def __init__(self) -> None:
        self._lock:      threading.Lock        = threading.Lock()
        self._store:     dict[str, BaseArtifact] = {}
        self._by_type:   dict[str, list[str]]  = {}  # type → [artifact_id]
        self._by_parent: dict[str, list[str]]  = {}  # parent_id → [child_id]

    def register(self, artifact: BaseArtifact) -> None:
        """Store artifact and update indexes.  Emits an event to the log."""
        with self._lock:
            self._store[artifact.artifact_id] = artifact
            self._by_type.setdefault(artifact.artifact_type, []).append(
                artifact.artifact_id
            )
            for pid in artifact.parent_ids:
                self._by_parent.setdefault(pid, []).append(artifact.artifact_id)

        # Append to durable log (fail-silent)
        try:
            from backend.events.log import append
            append(
                f"artifact.{artifact.artifact_type}.registered",
                payload=artifact.to_dict(),
                source="artifact_registry",
            )
        except Exception:
            pass

    def get(self, artifact_id: str) -> BaseArtifact | None:
        with self._lock:
            return self._store.get(artifact_id)

    def by_type(self, artifact_type: str) -> list[BaseArtifact]:
        with self._lock:
            ids = self._by_type.get(artifact_type, [])
            return [self._store[i] for i in ids if i in self._store]

    def children_of(self, parent_id: str) -> list[BaseArtifact]:
        with self._lock:
            ids = self._by_parent.get(parent_id, [])
            return [self._store[i] for i in ids if i in self._store]

    def count(self, artifact_type: str | None = None) -> int:
        with self._lock:
            if artifact_type:
                return len(self._by_type.get(artifact_type, []))
            return len(self._store)

    def deserialize(self, d: dict[str, Any]) -> BaseArtifact:
        """Reconstruct a typed artifact from its dict representation."""
        atype = d.get("artifact_type", "base")
        cls   = _TYPE_MAP.get(atype, BaseArtifact)
        return cls.from_dict(d)


_registry: ArtifactRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> ArtifactRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ArtifactRegistry()
    return _registry
