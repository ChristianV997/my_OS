"""backend.vector.schemas — data contracts for the vector cognition layer."""
from .vector_record    import VectorRecord
from .search_query     import SearchQuery
from .similarity_result import SimilarityResult

__all__ = ["VectorRecord", "SearchQuery", "SimilarityResult"]
