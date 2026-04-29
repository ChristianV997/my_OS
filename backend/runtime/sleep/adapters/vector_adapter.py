"""VectorAdapter — writes consolidated semantic units to the vector layer."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class VectorAdapter:
    """Bridges ConsolidationEngine outputs to the vector cognition fabric."""

    def index_semantic_units(self, domain_units: dict[str, list[dict[str, Any]]]) -> int:
        """Upsert semantic unit centroids as pattern_records in vector store."""
        try:
            from backend.vector.indexing      import pattern_record, index_batch
            from backend.vector.qdrant_client import get_store
            store   = get_store()
            records = []
            for domain, units in domain_units.items():
                for ud in units:
                    emb = ud.get("embedding", [])
                    if not emb:
                        continue
                    rec = pattern_record(
                        pattern_key=f"sleep:{domain}:{ud.get('label', ud.get('unit_id', ''))}",
                        vector=emb,
                        hook=ud.get("label", "") if domain == "hook" else "",
                        angle=ud.get("label", "") if domain == "angle" else "",
                        score=ud.get("score", 0.0),
                        domain=domain,
                        source="sleep_vector_adapter",
                    )
                    records.append(rec)
            if records:
                return index_batch(records, store=store)
            return 0
        except Exception as exc:
            log.warning("VectorAdapter.index_semantic_units failed: %s", exc)
            return 0

    def index_procedure_centroid(self, name: str, steps: list[dict], score: float) -> int:
        """Embed and index a procedure as a pattern vector."""
        try:
            from backend.vector.embeddings import embed_text
            from backend.vector.indexing   import pattern_record, index_batch
            from backend.vector.qdrant_client import get_store
            text   = name + " " + " ".join(str(s) for s in steps[:3])
            vec    = embed_text(text)
            rec    = pattern_record(
                pattern_key=f"procedure:{name}",
                vector=vec,
                score=score,
                domain="procedure",
                source="sleep_vector_adapter",
            )
            return index_batch([rec], store=get_store())
        except Exception as exc:
            log.warning("VectorAdapter.index_procedure_centroid failed: %s", exc)
            return 0
