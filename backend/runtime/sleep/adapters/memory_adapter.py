"""MemoryAdapter — cross-tier memory operations for the sleep runtime."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class MemoryAdapter:
    """Provides a unified interface across EpisodicStore, SemanticStore, ProceduralStore."""

    def episodic_stats(self) -> dict[str, Any]:
        try:
            from backend.memory.episodic import get_episodic_store
            store = get_episodic_store()
            return {"count": store.count()}
        except Exception:
            return {}

    def semantic_stats(self) -> dict[str, Any]:
        try:
            from backend.memory.semantic import get_semantic_store
            store = get_semantic_store()
            return {
                "generation": store.generation(),
                "total":      store.count(),
            }
        except Exception:
            return {}

    def procedural_stats(self) -> dict[str, Any]:
        try:
            from backend.memory.procedural import get_procedural_store
            store = get_procedural_store()
            return {"total": store.count()}
        except Exception:
            return {}

    def all_stats(self) -> dict[str, Any]:
        return {
            "episodic":   self.episodic_stats(),
            "semantic":   self.semantic_stats(),
            "procedural": self.procedural_stats(),
        }

    def promote_semantic_to_procedures(self, domain: str = "hook", top_k: int = 5) -> int:
        """Promote top semantic units into procedural memory as execution templates."""
        try:
            from backend.memory.semantic   import get_semantic_store
            from backend.memory.procedural import get_procedural_store
            sem   = get_semantic_store()
            proc  = get_procedural_store()
            top   = sem.top_by_score(domain, k=top_k)
            count = 0
            for unit in top:
                name = f"semantic_procedure:{domain}:{unit.label}"
                existing = proc.best_for_domain(domain, k=100)
                if any(p.name == name for p in existing):
                    continue
                proc.create(
                    name=name,
                    domain=domain,
                    steps=[{"action": "use_semantic_unit",
                            "label": unit.label,
                            "members": unit.cluster_members[:3]}],
                    avg_roas=unit.score * 3.0,  # heuristic: score → ROAS proxy
                )
                count += 1
            return count
        except Exception as exc:
            log.warning("promote_semantic_to_procedures failed: %s", exc)
            return 0
