"""backend.vector — replay-safe semantic cognition infrastructure.

Provides deterministic vector indexing, semantic retrieval, and similarity
search layered on top of the existing inference embedding pipeline and
RuntimeReplayStore. All operations preserve replay_hash / sequence_id
lineage and emit telemetry via the existing PubSubBroker.
"""
from __future__ import annotations
