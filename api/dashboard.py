from fastapi import APIRouter
import os
import threading
import time

from backend.core import serializer
from backend.core.state import SystemState

router = APIRouter()
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = max(1, int(os.getenv("UPOS_DASHBOARD_CACHE_TTL_SEC", "2")))
_STATE_CACHE = {"value": None, "expires_at": 0.0}


def _load_shared_state() -> SystemState:
    now = time.monotonic()
    with _CACHE_LOCK:
        if _STATE_CACHE["value"] is not None and now < _STATE_CACHE["expires_at"]:
            return _STATE_CACHE["value"]
    loaded = serializer.load()
    state = loaded if loaded is not None else SystemState()
    with _CACHE_LOCK:
        _STATE_CACHE["value"] = state
        _STATE_CACHE["expires_at"] = now + _CACHE_TTL_SECONDS
    return state


@router.get("/product/{product_id}")
def product_lifecycle(product_id: str):
    state = _load_shared_state()
    events = [row for row in state.event_log.rows if row.get("product_id") == product_id]

    return [
        {
            "timestamp": event.get("timestamp"),
            "roas": event.get("roas", 0),
            "spend": event.get("cost", event.get("spend", 0)),
            "revenue": event.get("revenue", 0),
        }
        for event in events
    ]
