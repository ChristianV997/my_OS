"""backend.vector.collections — canonical collection definitions.

Every named collection used by the vector layer is declared here.
Consumers import these constants; raw string literals are forbidden.
"""
from __future__ import annotations
from dataclasses import dataclass

# ── collection name constants ─────────────────────────────────────────────────

HOOKS       = "hooks"
PRODUCTS    = "products"
CAMPAIGNS   = "campaigns"
SIGNALS     = "signals"
PATTERNS    = "patterns"
ANGLES      = "angles"
CREATIVES   = "creatives"

ALL_COLLECTIONS: tuple[str, ...] = (
    HOOKS, PRODUCTS, CAMPAIGNS, SIGNALS, PATTERNS, ANGLES, CREATIVES,
)

# ── collection metadata ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class CollectionSpec:
    name:        str
    vector_size: int   = 384
    distance:    str   = "Cosine"   # Cosine | Dot | Euclid

COLLECTION_SPECS: dict[str, CollectionSpec] = {
    c: CollectionSpec(name=c) for c in ALL_COLLECTIONS
}


def get_spec(name: str) -> CollectionSpec:
    if name not in COLLECTION_SPECS:
        raise KeyError(f"Unknown vector collection: {name!r}")
    return COLLECTION_SPECS[name]
