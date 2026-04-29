"""ReinforcementMemory — semantic memory backed by ROAS outcomes.

Maps hook+product pairs to their real ROAS outcomes so the learning loop
can retrieve semantically similar winning combinations.
"""
from __future__ import annotations

import time
from typing import Any

from ..embeddings     import embed_text
from ..normalization  import deterministic_id, stamp_lineage
from ..schemas        import VectorRecord, SearchQuery, SimilarityResult
from ..collections    import PATTERNS
from ..telemetry      import emit_indexed


class ReinforcementMemory:
    """Append-only log of (hook, angle, product, roas) outcomes as vectors.

    Retrieval surfaces the highest-ROAS clusters semantically similar to
    a new candidate creative.
    """

    def __init__(self, store=None) -> None:
        from ..qdrant_client import get_store
        self._store = store or get_store()

    def record_outcome(
        self,
        hook: str,
        angle: str,
        product: str,
        roas: float,
        phase: str = "",
        sequence_id: str = "",
        **meta: Any,
    ) -> None:
        """Embed the creative context and store it with its ROAS outcome."""
        text = f"{hook} {angle} {product}"
        from ..normalization import normalize
        from backend.inference.embeddings import embed_text as _embed
        vec  = normalize(_embed(text))
        key  = f"{hook}:{angle}:{product}:{roas:.4f}:{time.time()}"
        rid  = deterministic_id("reinforcement", key)
        payload = stamp_lineage(
            {"hook": hook, "angle": angle, "product": product,
             "roas": roas, "phase": phase, **meta},
            source="reinforcement",
            sequence_id=sequence_id,
        )
        record = VectorRecord(
            record_id=rid,
            vector=vec,
            payload=payload,
            collection=PATTERNS,
            source="reinforcement",
            sequence_id=sequence_id,
        )
        self._store.upsert([record])
        emit_indexed(PATTERNS, 1, source="reinforcement_memory")

    def find_winners(
        self,
        query: str,
        top_k: int = 10,
        min_roas: float = 0.0,
    ) -> list[SimilarityResult]:
        """Find semantically similar past winners above *min_roas*."""
        from ..normalization import normalize
        from backend.inference.embeddings import embed_text as _embed
        vec   = normalize(_embed(query))
        store = self._store
        q = SearchQuery(
            vector=vec,
            collection=PATTERNS,
            top_k=top_k * 3,  # over-fetch then filter
            score_threshold=0.0,
        )
        results = store.search(q)
        if min_roas > 0.0:
            results = [r for r in results
                       if r.payload.get("roas", 0.0) >= min_roas]
        return results[:top_k]

    def count(self) -> int:
        return self._store.count(PATTERNS)
