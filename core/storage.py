import json
import os
import threading

EVENTS_PATH = "backend/state/events.jsonl"
_WRITE_LOCK = threading.Lock()


def store_event(event):
    """Append a JSON-serializable event dict to local JSONL storage."""
    store_events([event])


def store_events(events):
    """Append JSON-serializable event dicts to local JSONL storage in one write lock."""
    if not events:
        return
    os.makedirs(os.path.dirname(EVENTS_PATH), exist_ok=True)

    with _WRITE_LOCK:
        with open(EVENTS_PATH, "a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event) + "\n")
