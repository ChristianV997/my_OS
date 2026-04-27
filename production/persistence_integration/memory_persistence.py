from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from memory.semantic_runtime.graph import (
    semantic_runtime_graph,
)

from production.persistence_backends.vector_store import (
    vector_store,
)


@dataclass(slots=True)
class PersistedMemory:
    persisted: bool
    key: str
    metadata: Dict


class SemanticMemoryPersistence:
    """
    Durable semantic runtime memory persistence.
    """

    def persist_node(
        self,
        *,
        key: str,
        embedding: List[
            float
        ],
        metadata: Dict,
    ) -> PersistedMemory:
        vector_store.upsert(
            key=key,
            embedding=embedding,
            metadata=metadata,
        )

        return PersistedMemory(
            persisted=True,
            key=key,
            metadata=metadata,
        )

    def persist_graph(
        self,
    ):
        for node_id, node in (
            semantic_runtime_graph
            .nodes.items()
        ):
            vector_store.upsert(
                key=node_id,
                embedding=[0.0],
                metadata={
                    "node_type": (
                        node.node_type
                    ),
                },
            )


semantic_memory_persistence = (
    SemanticMemoryPersistence()
)
