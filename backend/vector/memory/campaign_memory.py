"""CampaignMemory — semantic store for launched campaign embeddings."""
from __future__ import annotations

from typing import Any

from ..embeddings       import embed_text
from ..indexing         import campaign_record
from ..semantic_search  import find_similar_campaigns
from ..schemas          import SimilarityResult
from ..telemetry        import emit_indexed


class CampaignMemory:
    """Stores campaign artifacts as embeddings for semantic retrieval and similarity."""

    def __init__(self, store=None) -> None:
        from ..qdrant_client import get_store
        self._store = store or get_store()

    def index_campaign(
        self,
        campaign_id: str,
        product: str,
        hook: str,
        angle: str,
        roas: float = 0.0,
        phase: str = "",
        **meta: Any,
    ) -> int:
        """Embed the campaign creative context and upsert into campaigns collection."""
        text = f"{product} {hook} {angle}"
        vec  = embed_text(text)
        rec  = campaign_record(
            campaign_id, vec,
            product=product, hook=hook, angle=angle,
            roas=roas, phase=phase, **meta,
        )
        n = self._store.upsert([rec])
        emit_indexed("campaigns", n, source="campaign_memory")
        return n

    def find_similar(self, query: str, top_k: int = 10) -> list[SimilarityResult]:
        return find_similar_campaigns(query, top_k=top_k)

    def count(self) -> int:
        return self._store.count("campaigns")
