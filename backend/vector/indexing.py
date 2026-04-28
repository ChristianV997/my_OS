"""backend.vector.indexing — high-level indexing pipeline.

Provides ``index_record`` and ``index_batch`` which:
  1. Validate the input text and metadata.
  2. Embed via the inference router (reusing cache).
  3. Build a VectorRecord with full lineage.
  4. Upsert into the Qdrant collection.
  5. Emit telemetry.

This is the single entry point for all vector writes in the runtime.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from backend.vector.schemas.vector_record import VectorRecord
from backend.vector.embeddings import embed_for_index, embed_batch_for_index

_log = logging.getLogger(__name__)


def index_record(
    text: str,
    collection: str,
    source_id: str,
    source_type: str,
    payload: dict[str, Any] | None = None,
    embedding_model: str = "default",
    embedding_provider: str = "auto",
    use_cache: bool = True,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> VectorRecord | None:
    """Embed *text* and index it into *collection*.

    Returns the VectorRecord on success, None on failure.
    """
    from backend.vector.qdrant_client import get_vector_store

    record = embed_for_index(
        text=text,
        collection=collection,
        source_id=source_id,
        source_type=source_type,
        payload=payload,
        model=embedding_model,
        provider=embedding_provider,
        use_cache=use_cache,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )
    if record is None:
        return None

    store = get_vector_store()
    ok = store.upsert(record)
    if not ok:
        _log.warning("index_record_upsert_failed source_id=%s", source_id)
        return None
    return record


def index_batch(
    items: list[dict[str, Any]],
    collection: str,
    source_type: str,
    embedding_model: str = "default",
    embedding_provider: str = "auto",
    use_cache: bool = True,
) -> int:
    """Embed and index a batch of items.

    Each item must have:
      - "text"       : str
      - "source_id"  : str
      - "payload"    : dict  (optional)
      - "replay_hash": str   (optional)
      - "sequence_id": int   (optional)

    Returns count of successfully indexed records.
    """
    from backend.vector.qdrant_client import get_vector_store

    records = embed_batch_for_index(
        items=items,
        collection=collection,
        source_type=source_type,
        model=embedding_model,
        provider=embedding_provider,
        use_cache=use_cache,
    )
    if not records:
        return 0
    store = get_vector_store()
    return store.upsert_batch(records)
