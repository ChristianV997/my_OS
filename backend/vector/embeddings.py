"""backend.vector.embeddings — embedding bridge for the vector layer.

Wraps ``backend.inference.embeddings`` to produce VectorRecord-ready
float vectors with full lineage fields.  Does NOT duplicate the
inference embedding cache — it reuses it directly.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def embed_for_index(
    text: str,
    collection: str,
    source_id: str,
    source_type: str,
    payload: dict[str, Any] | None = None,
    model: str = "default",
    provider: str = "auto",
    use_cache: bool = True,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> VectorRecord | None:
    """Embed *text* and return a VectorRecord ready for indexing.

    Returns None if the embedding call fails.
    """
    from backend.inference.embeddings import embed_text

    t0 = time.time()
    vector = embed_text(text, model=model, provider=provider, use_cache=use_cache)
    if not vector:
        _log.warning("embed_for_index_failed source_id=%s", source_id)
        return None

    return VectorRecord(
        collection=collection,
        source_id=source_id,
        source_type=source_type,
        vector=vector,
        payload=payload or {},
        replay_hash=replay_hash,
        sequence_id=sequence_id,
        embedding_model=model,
        embedding_provider=provider,
    )


def embed_batch_for_index(
    items: list[dict[str, Any]],
    collection: str,
    source_type: str,
    model: str = "default",
    provider: str = "auto",
    use_cache: bool = True,
) -> list[VectorRecord]:
    """Embed a batch of items and return VectorRecords for indexing.

    Each item in *items* must have:
      - "text"       : str   — content to embed
      - "source_id"  : str   — originating document ID
      - "payload"    : dict  — (optional) metadata
      - "replay_hash": str   — (optional) deterministic hash
      - "sequence_id": int   — (optional) ordering key
    """
    from backend.inference.embeddings import embed_texts

    texts = [item["text"] for item in items]
    vectors = embed_texts(texts, model=model, provider=provider, use_cache=use_cache)

    records: list[VectorRecord] = []
    for item, vector in zip(items, vectors):
        if not vector:
            _log.warning("embed_batch_skip source_id=%s", item.get("source_id", "?"))
            continue
        records.append(
            VectorRecord(
                collection=collection,
                source_id=item["source_id"],
                source_type=source_type,
                vector=vector,
                payload=item.get("payload", {}),
                replay_hash=item.get("replay_hash"),
                sequence_id=item.get("sequence_id"),
                embedding_model=model,
                embedding_provider=provider,
            )
        )
    return records


def embed_query(
    text: str,
    model: str = "default",
    provider: str = "auto",
    use_cache: bool = True,
) -> list[float]:
    """Embed a search query string and return the raw float vector."""
    from backend.inference.embeddings import embed_text

    return embed_text(text, model=model, provider=provider, use_cache=use_cache)
