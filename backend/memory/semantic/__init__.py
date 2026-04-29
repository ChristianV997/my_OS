"""backend.memory.semantic — compressed abstraction layer (distilled knowledge)."""
from .store import SemanticStore, SemanticUnit

import threading

_store_instance: SemanticStore | None = None
_lock = threading.Lock()


def get_semantic_store() -> SemanticStore:
    global _store_instance
    if _store_instance is None:
        with _lock:
            if _store_instance is None:
                _store_instance = SemanticStore()
    return _store_instance


__all__ = ["SemanticStore", "SemanticUnit", "get_semantic_store"]
