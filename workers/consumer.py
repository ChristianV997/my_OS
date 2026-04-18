import json
import time

from core.storage import store_event
from core.stream import consume


def run_once():
    events = consume()
    stored = 0

    for _, messages in events:
        for _, payload in messages:
            store_event(json.loads(payload["data"]))
            stored += 1

    return stored


def run(poll_seconds=1):
    while True:
        run_once()
        time.sleep(poll_seconds)
