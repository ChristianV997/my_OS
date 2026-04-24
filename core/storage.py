import json
import os
import threading

EVENTS_PATH = "backend/state/events.jsonl"
_JSON_BASE = "data"
_WRITE_LOCK = threading.Lock()


def store_event(event):
    """Append a JSON-serializable event dict to local JSONL storage."""
    os.makedirs(os.path.dirname(EVENTS_PATH), exist_ok=True)

    with _WRITE_LOCK:
        with open(EVENTS_PATH, "a") as handle:
            handle.write(json.dumps(event) + "\n")


def save_json(name, data, base=None):
    """Persist *data* as a named JSON file under *base* directory."""
    directory = base or _JSON_BASE
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{name}.json")
    with open(path, "w") as fh:
        json.dump(data, fh)


def load_json(name, default=None, base=None):
    """Load a named JSON file from *base* directory; return *default* if absent."""
    directory = base or _JSON_BASE
    path = os.path.join(directory, f"{name}.json")
    if not os.path.exists(path):
        return default
    with open(path, "r") as fh:
        return json.load(fh)
