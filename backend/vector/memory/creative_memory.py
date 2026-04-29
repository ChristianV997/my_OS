"""CreativeMemory — indexes hooks/angles and retrieves semantically similar creatives."""
from __future__ import annotations

from typing import Any

from ..embeddings     import embed_text, embed_batch
from ..indexing       import hook_record, angle_record, creative_record, index_batch
from ..semantic_search import find_similar_hooks, find_creatives_by_hook
from ..schemas        import SimilarityResult
from ..telemetry      import emit_indexed


class CreativeMemory:
    """Semantic store for creative assets (hooks, angles, ad creatives).

    All writes use deterministic UUID5 IDs — safe to call repeatedly with
    the same data.
    """

    def __init__(self, store=None) -> None:
        from ..qdrant_client import get_store
        self._store = store or get_store()

    # ── indexing ──────────────────────────────────────────────────────────────

    def index_hooks(self, hooks: list[str], **meta: Any) -> int:
        if not hooks:
            return 0
        vecs    = embed_batch(hooks)
        records = [hook_record(h, v, **meta) for h, v in zip(hooks, vecs)]
        n = self._store.upsert(records)
        emit_indexed("hooks", n, source="creative_memory")
        return n

    def index_angles(self, angles: list[str], **meta: Any) -> int:
        if not angles:
            return 0
        vecs    = embed_batch(angles)
        records = [angle_record(a, v, **meta) for a, v in zip(angles, vecs)]
        n = self._store.upsert(records)
        emit_indexed("angles", n, source="creative_memory")
        return n

    def index_creative(
        self,
        creative_id: str,
        hook: str,
        product: str,
        roas: float = 0.0,
        **meta: Any,
    ) -> int:
        vec    = embed_text(f"{hook} {product}")
        record = creative_record(creative_id, vec, hook=hook, product=product,
                                 roas=roas, **meta)
        n = self._store.upsert([record])
        emit_indexed("creatives", n, source="creative_memory")
        return n

    # ── retrieval ─────────────────────────────────────────────────────────────

    def similar_hooks(self, query: str, top_k: int = 10) -> list[SimilarityResult]:
        return find_similar_hooks(query, top_k=top_k)

    def similar_creatives(self, hook: str, top_k: int = 10) -> list[SimilarityResult]:
        return find_creatives_by_hook(hook, top_k=top_k)

    def hook_count(self) -> int:
        return self._store.count("hooks")

    def creative_count(self) -> int:
        return self._store.count("creatives")
