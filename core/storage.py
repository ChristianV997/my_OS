import json
import os
import threading

EVENTS_PATH = "backend/state/events.jsonl"
_WRITE_LOCK = threading.Lock()


def store_event(event):
    os.makedirs(os.path.dirname(EVENTS_PATH), exist_ok=True)

    with _WRITE_LOCK:
        with open(EVENTS_PATH, "a") as handle:
            handle.write(json.dumps(event) + "\n")
