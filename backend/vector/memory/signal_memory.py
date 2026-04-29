"""SignalMemory — semantic store for market signals (trends, keywords, events)."""
from __future__ import annotations

from typing import Any

from ..embeddings      import embed_text, embed_batch
from ..indexing        import signal_record, index_batch
from ..semantic_search import find_similar_signals
from ..schemas         import SimilarityResult
from ..telemetry       import emit_indexed


class SignalMemory:
    """Indexes market signals by semantic embedding for retrieval and clustering."""

    def __init__(self, store=None) -> None:
        from ..qdrant_client import get_store
        self._store = store or get_store()

    def index_signals(
        self,
        signals: list[dict[str, Any]],
        text_key: str = "keyword",
        signal_type: str = "",
    ) -> int:
        """Index a list of signal dicts. ``text_key`` names the field to embed."""
        if not signals:
            return 0
        texts   = [str(s.get(text_key, "")) for s in signals]
        vecs    = embed_batch(texts)
        records = []
        for s, text, vec in zip(signals, texts, vecs):
            key   = s.get("id") or text
            stype = s.get("type") or signal_type
            rec   = signal_record(key, vec, signal_type=stype,
                                  **{k: v for k, v in s.items()
                                     if k not in ("id", "type")})
            records.append(rec)
        n = self._store.upsert(records)
        emit_indexed("signals", n, source="signal_memory")
        return n

    def index_keyword(self, keyword: str, **meta: Any) -> int:
        vec = embed_text(keyword)
        rec = signal_record(keyword, vec, signal_type="keyword", **meta)
        n   = self._store.upsert([rec])
        emit_indexed("signals", n, source="signal_memory")
        return n

    def find_similar(self, query: str, top_k: int = 10) -> list[SimilarityResult]:
        return find_similar_signals(query, top_k=top_k)

    def count(self) -> int:
        return self._store.count("signals")
