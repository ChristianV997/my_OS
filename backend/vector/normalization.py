"""backend.vector.normalization — vector normalization utilities.

Provides L2 normalisation and basic sanitisation so all vectors entering
the index have consistent magnitude, enabling cosine similarity via
dot-product on normalised vectors.
"""
from __future__ import annotations

import math
from typing import Sequence


def l2_norm(vector: list[float]) -> float:
    """Return the L2 (Euclidean) norm of a vector."""
    return math.sqrt(sum(x * x for x in vector))


def normalize(vector: list[float]) -> list[float]:
    """Return a unit-length (L2-normalised) copy of *vector*.

    Returns the zero vector unchanged to avoid division by zero.
    """
    if not vector:
        return vector
    norm = l2_norm(vector)
    if norm == 0.0:
        return list(vector)
    return [x / norm for x in vector]


def normalize_batch(vectors: list[list[float]]) -> list[list[float]]:
    """Normalise a batch of vectors in-place (returns new list)."""
    return [normalize(v) for v in vectors]


def is_zero_vector(vector: list[float]) -> bool:
    """Return True if all elements are zero (or vector is empty)."""
    return not vector or all(x == 0.0 for x in vector)


def pad_or_truncate(vector: list[float], dim: int) -> list[float]:
    """Return a copy of *vector* with exactly *dim* dimensions.

    Pads with zeros if shorter; truncates if longer.
    """
    if len(vector) == dim:
        return list(vector)
    if len(vector) < dim:
        return list(vector) + [0.0] * (dim - len(vector))
    return list(vector[:dim])


def vectors_same_dim(vectors: list[list[float]]) -> bool:
    """Return True if all vectors share the same dimensionality."""
    if not vectors:
        return True
    dim = len(vectors[0])
    return all(len(v) == dim for v in vectors)
