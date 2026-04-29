"""PatternMemory — semantic retrieval layer over PatternStore scores.

Bridges the existing PatternStore (hook_scores / angle_scores dicts) with
the vector layer so that scores can be retrieved by semantic similarity
rather than exact key lookup.
"""
from __future__ import annotations

from typing import Any

from ..embeddings     import embed_text, embed_batch
from ..indexing       import pattern_record, index_batch
from ..semantic_search import find_similar_patterns
from ..schemas        import SimilarityResult
from ..telemetry      import emit_indexed


class PatternMemory:
    """Indexes PatternStore scores into the vector layer for semantic search."""

    def __init__(self, store=None) -> None:
        from ..qdrant_client import get_store
        self._store = store or get_store()

    def sync_from_pattern_store(self) -> int:
        """Pull hook/angle scores from PatternStore and (re-)index them."""
        try:
            from core.content.patterns import pattern_store
            snap = pattern_store.snapshot()
        except Exception:
            return 0

        records = []
        for hook, score in snap.get("hook_scores", {}).items():
            vec = embed_text(hook)
            records.append(pattern_record(
                f"hook:{hook}", vec, hook=hook, score=score,
            ))
        for angle, score in snap.get("angle_scores", {}).items():
            vec = embed_text(angle)
            records.append(pattern_record(
                f"angle:{angle}", vec, angle=angle, score=score,
            ))

        if not records:
            return 0
        n = self._store.upsert(records)
        emit_indexed("patterns", n, source="pattern_memory")
        return n

    def index_hook_scores(self, hook_scores: dict[str, float]) -> int:
        if not hook_scores:
            return 0
        hooks = list(hook_scores.keys())
        vecs  = embed_batch(hooks)
        records = [
            pattern_record(f"hook:{h}", v, hook=h, score=hook_scores[h])
            for h, v in zip(hooks, vecs)
        ]
        n = self._store.upsert(records)
        emit_indexed("patterns", n, source="pattern_memory")
        return n

    def index_angle_scores(self, angle_scores: dict[str, float]) -> int:
        if not angle_scores:
            return 0
        angles = list(angle_scores.keys())
        vecs   = embed_batch(angles)
        records = [
            pattern_record(f"angle:{a}", v, angle=a, score=angle_scores[a])
            for a, v in zip(angles, vecs)
        ]
        n = self._store.upsert(records)
        emit_indexed("patterns", n, source="pattern_memory")
        return n

    def find_similar(self, query: str, top_k: int = 10) -> list[SimilarityResult]:
        return find_similar_patterns(query, top_k=top_k)

    def count(self) -> int:
        return self._store.count("patterns")
