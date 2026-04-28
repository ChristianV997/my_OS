"""backend.vector.adapters.research_adapter — research → vector indexing.

Consumes records from TrendRecordStore and indexes them into the
research and signals Qdrant collections.  Reuses the existing
``backend.research.trend_store.TrendRecordStore`` contract directly.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_RESEARCH
from backend.vector.memory.signal_memory import index_signals_batch
from backend.vector.indexing import index_batch
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def ingest_trend_records(
    records: list[dict[str, Any]],
    also_index_as_signals: bool = True,
) -> dict[str, int]:
    """Index a list of TrendRecordStore records into the vector layer.

    Parameters
    ----------
    records              — list of research record dicts (TrendRecordStore schema)
    also_index_as_signals — if True, also index into the signals collection

    Returns
    -------
    dict with keys "research_indexed" and "signals_indexed"
    """
    if not records:
        return {"research_indexed": 0, "signals_indexed": 0}

    # Build items for the research collection
    research_items = []
    for r in records:
        topic = r.get("topic", "")
        raw = r.get("raw", {})
        text_parts = [topic]
        if isinstance(raw, dict):
            summary = raw.get("summary") or raw.get("content") or raw.get("title", "")
            if summary:
                text_parts.append(str(summary))
        text = " ".join(p for p in text_parts if p).strip()
        if not text:
            continue
        research_items.append({
            "text": text,
            "source_id": r.get("id", ""),
            "payload": {
                "topic": topic,
                "intent": r.get("intent", "unknown"),
                "source": r.get("source", ""),
                "velocity": r.get("velocity", 0.0),
                "competition": r.get("competition", 0.0),
                "confidence": r.get("confidence", 0.0),
                "freshness_ts": r.get("freshness_ts", ""),
            },
            "replay_hash": None,
            "sequence_id": None,
        })

    research_indexed = index_batch(
        items=research_items,
        collection=COLLECTION_RESEARCH,
        source_type="research",
    )

    signals_indexed = 0
    if also_index_as_signals:
        signals_indexed = index_signals_batch(records)

    return {"research_indexed": research_indexed, "signals_indexed": signals_indexed}


def ingest_from_trend_store(
    db_path: str = "backend/state/research.db",
    limit: int = 500,
    also_index_as_signals: bool = True,
) -> dict[str, int]:
    """Pull records from TrendRecordStore and ingest into vector layer.

    Parameters
    ----------
    db_path              — path to the SQLite database
    limit                — max records to pull
    also_index_as_signals — if True, also index into signals collection
    """
    try:
        from backend.research.trend_store import TrendRecordStore
        store = TrendRecordStore(path=db_path)
        records = store.findTopN(limit)
    except Exception as exc:
        _log.warning("ingest_from_trend_store_failed error=%s", exc)
        return {"research_indexed": 0, "signals_indexed": 0}
    return ingest_trend_records(records, also_index_as_signals=also_index_as_signals)
