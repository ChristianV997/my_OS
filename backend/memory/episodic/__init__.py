"""backend.memory.episodic — raw event and execution history (highest fidelity)."""
from .store import EpisodicStore, Episode

import threading

_store_instance: EpisodicStore | None = None
_lock = threading.Lock()


def get_episodic_store() -> EpisodicStore:
    global _store_instance
    if _store_instance is None:
        with _lock:
            if _store_instance is None:
                _store_instance = EpisodicStore()
    return _store_instance


__all__ = ["EpisodicStore", "Episode", "get_episodic_store"]
