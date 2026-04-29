"""backend.vector.normalization — vector normalization and lineage stamping."""
from __future__ import annotations
import math
import time
import uuid
from typing import Any

_NAMESPACE = uuid.UUID("7a9d8f3c-1b2e-4a5f-9c0d-3e6f8a1b4c7d")


def normalize(vector: list[float]) -> list[float]:
    """Return the L2-normalized form of *vector*; returns zeros on zero-norm."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm < 1e-12:
        return [0.0] * len(vector)
    return [x / norm for x in vector]


def deterministic_id(source: str, key: str) -> str:
    """UUID5 from ``source:key`` — same inputs always produce the same ID."""
    return str(uuid.uuid5(_NAMESPACE, f"{source}:{key}"))


def stamp_lineage(
    payload: dict[str, Any],
    source: str,
    sequence_id: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return *payload* augmented with standard lineage fields.

    Does not mutate the original dict.
    """
    merged = dict(payload)
    merged.setdefault("_source",   source)
    merged.setdefault("_ts",       time.time())
    if sequence_id:
        merged["_sequence_id"] = sequence_id
    if extra:
        merged.update(extra)
    return merged
