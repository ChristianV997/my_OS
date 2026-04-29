"""SearchQuery — parameters for semantic vector search."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing      import Any


@dataclass
class SearchQuery:
    """Encapsulates a semantic search request against a vector collection.

    ``vector`` is the pre-computed query embedding.  The caller is
    responsible for embedding the raw text before constructing this object.
    """
    vector:      list[float]
    collection:  str
    top_k:       int             = 10
    score_threshold: float       = 0.0    # minimum cosine similarity to return
    filter:      dict[str, Any]  = field(default_factory=dict)
    include_payload: bool        = True
    sequence_id: str             = ""
