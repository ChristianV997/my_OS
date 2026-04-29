"""backend.memory.procedural — reusable workflow recipes and execution policies."""
from .store import ProceduralStore, Procedure

import threading

_store_instance: ProceduralStore | None = None
_lock = threading.Lock()


def get_procedural_store() -> ProceduralStore:
    global _store_instance
    if _store_instance is None:
        with _lock:
            if _store_instance is None:
                _store_instance = ProceduralStore()
    return _store_instance


__all__ = ["ProceduralStore", "Procedure", "get_procedural_store"]
