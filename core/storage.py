import json
import os

EVENTS_PATH = "backend/state/events.jsonl"



def store_event(event):
    os.makedirs(os.path.dirname(EVENTS_PATH), exist_ok=True)

    with open(EVENTS_PATH, "a") as handle:
        handle.write(json.dumps(event) + "\n")
