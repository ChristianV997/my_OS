"""backend.vector — vector cognition fabric.

Public API:
    get_store()         → VectorStore singleton (Qdrant or in-memory fallback)
    search()            → semantic search against a single collection
    search_all()        → multi-collection search
    find_similar_hooks()
    find_similar_products()
    find_similar_campaigns()
    find_similar_signals()
    find_similar_patterns()
    rank_by_similarity()
    index_hooks()
    index_products()
    index_angles()
    cosine()
    top_k()
    cluster_hooks()
    winner_centroid()

Memory modules (domain-specific semantic stores):
    CreativeMemory
    SignalMemory
    CampaignMemory
    ReinforcementMemory
    PatternMemory

Adapters (bridge to operational data sources):
    InferenceAdapter
    ReplayAdapter
    ResearchAdapter
    TelemetryAdapter
"""

from .qdrant_client  import get_store, reset_store, InMemoryVectorStore
from .collections    import HOOKS, PRODUCTS, CAMPAIGNS, SIGNALS, PATTERNS, ANGLES, CREATIVES
from .schemas        import VectorRecord, SearchQuery, SimilarityResult
from .similarity     import cosine, top_k, batch_cosine, affinity_matrix
from .clustering     import cluster_hooks, winner_centroid, kmeans
from .indexing       import index_hooks, index_products, index_angles, index_batch
from .embeddings     import embed_text, embed_batch, embed_dict
from .semantic_search import (
    search, search_all,
    find_similar_hooks, find_similar_products, find_similar_campaigns,
    find_similar_signals, find_similar_patterns, find_winning_angles,
    find_creatives_by_hook, rank_by_similarity,
)
from .memory import (
    CreativeMemory, SignalMemory, CampaignMemory,
    ReinforcementMemory, PatternMemory,
)
from .adapters import (
    InferenceAdapter, ReplayAdapter, ResearchAdapter, TelemetryAdapter,
)

__all__ = [
    # store
    "get_store", "reset_store", "InMemoryVectorStore",
    # collection names
    "HOOKS", "PRODUCTS", "CAMPAIGNS", "SIGNALS", "PATTERNS", "ANGLES", "CREATIVES",
    # schemas
    "VectorRecord", "SearchQuery", "SimilarityResult",
    # similarity
    "cosine", "top_k", "batch_cosine", "affinity_matrix",
    # clustering
    "cluster_hooks", "winner_centroid", "kmeans",
    # indexing
    "index_hooks", "index_products", "index_angles", "index_batch",
    # embeddings
    "embed_text", "embed_batch", "embed_dict",
    # search
    "search", "search_all",
    "find_similar_hooks", "find_similar_products", "find_similar_campaigns",
    "find_similar_signals", "find_similar_patterns", "find_winning_angles",
    "find_creatives_by_hook", "rank_by_similarity",
    # memory
    "CreativeMemory", "SignalMemory", "CampaignMemory",
    "ReinforcementMemory", "PatternMemory",
    # adapters
    "InferenceAdapter", "ReplayAdapter", "ResearchAdapter", "TelemetryAdapter",
]
