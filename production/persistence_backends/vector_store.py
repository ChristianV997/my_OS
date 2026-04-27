from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List


VECTOR_STORE_PATH = Path(
    "backend/state/vector_store.json"
)


@dataclass(slots=True)
class SemanticVector:
    key: str
    embedding: List[float]
    metadata: Dict
    timestamp: float


class VectorStore:
    """
    Durable semantic vector persistence.
    """

    def __init__(self):
        self.vectors: Dict[
            str,
            SemanticVector,
        ] = {}

        self._load()

    def _load(self):
        if not VECTOR_STORE_PATH.exists():
            return

        payload = json.loads(
            VECTOR_STORE_PATH
            .read_text()
        )

        for key, value in (
            payload.items()
        ):
            self.vectors[key] = (
                SemanticVector(
                    **value
                )
            )

    def _persist(self):
        VECTOR_STORE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        VECTOR_STORE_PATH.write_text(
            json.dumps(
                {
                    key: asdict(
                        value
                    )
                    for key, value in (
                        self.vectors
                        .items()
                    )
                },
                indent=2,
            )
        )

    def upsert(
        self,
        *,
        key: str,
        embedding: List[
            float
        ],
        metadata: Dict,
    ) -> SemanticVector:
        vector = SemanticVector(
            key=key,
            embedding=embedding,
            metadata=metadata,
            timestamp=time.time(),
        )

        self.vectors[key] = (
            vector
        )

        self._persist()

        return vector

    def query(
        self,
        limit: int = 10,
    ) -> List[
        SemanticVector
    ]:
        return sorted(
            self.vectors.values(),
            key=lambda v: (
                v.timestamp
            ),
            reverse=True,
        )[:limit]


vector_store = VectorStore()
