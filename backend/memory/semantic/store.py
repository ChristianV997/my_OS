"""SemanticStore — compressed abstraction layer over episodic memory.

Semantic memory holds distilled knowledge: hook clusters, angle archetypes,
signal themes, product profiles.  It is produced by the consolidation
runtime (Phase 4) by clustering episodic episodes and compressing them into
SemanticAsset objects.

Unlike episodic memory, semantic memory is:
  - compressed (many episodes → one semantic unit)
  - indexed by concept label for fast lookup
  - versioned (each consolidation pass bumps a generation counter)
  - exportable to the vector layer (SemanticAsset.embedding)
"""
from __future__ import annotations

import threading
import time
from typing import Any


class SemanticUnit:
    """One compressed concept in semantic memory."""
    __slots__ = ("unit_id", "label", "domain", "embedding", "cluster_members",
                 "score", "generation", "ts", "metadata")

    def __init__(
        self,
        unit_id:         str,
        label:           str,
        domain:          str,           # hook | angle | signal | product
        embedding:       list[float],
        cluster_members: list[str],
        score:           float = 0.0,
        generation:      int   = 0,
        metadata:        dict[str, Any] | None = None,
    ) -> None:
        self.unit_id         = unit_id
        self.label           = label
        self.domain          = domain
        self.embedding       = embedding
        self.cluster_members = cluster_members
        self.score           = score
        self.generation      = generation
        self.ts              = time.time()
        self.metadata        = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id":         self.unit_id,
            "label":           self.label,
            "domain":          self.domain,
            "embedding":       self.embedding,
            "cluster_members": self.cluster_members,
            "score":           self.score,
            "generation":      self.generation,
            "ts":              self.ts,
            "metadata":        self.metadata,
        }


class SemanticStore:
    """Thread-safe store of SemanticUnit objects indexed by domain and label."""

    def __init__(self) -> None:
        self._lock:      threading.Lock                    = threading.Lock()
        self._units:     dict[str, SemanticUnit]           = {}  # unit_id → unit
        self._by_domain: dict[str, dict[str, SemanticUnit]] = {}  # domain → label → unit
        self._generation: int                              = 0

    def upsert(self, unit: SemanticUnit) -> None:
        with self._lock:
            self._units[unit.unit_id] = unit
            self._by_domain.setdefault(unit.domain, {})[unit.label] = unit

    def get_by_label(self, domain: str, label: str) -> SemanticUnit | None:
        with self._lock:
            return self._by_domain.get(domain, {}).get(label)

    def domain_units(self, domain: str) -> list[SemanticUnit]:
        with self._lock:
            return list(self._by_domain.get(domain, {}).values())

    def top_by_score(self, domain: str, k: int = 10) -> list[SemanticUnit]:
        units = self.domain_units(domain)
        return sorted(units, key=lambda u: u.score, reverse=True)[:k]

    def bump_generation(self) -> int:
        with self._lock:
            self._generation += 1
            return self._generation

    def generation(self) -> int:
        with self._lock:
            return self._generation

    def count(self, domain: str | None = None) -> int:
        with self._lock:
            if domain:
                return len(self._by_domain.get(domain, {}))
            return len(self._units)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "generation": self._generation,
                "domains": {
                    d: [u.to_dict() for u in units.values()]
                    for d, units in self._by_domain.items()
                },
            }
