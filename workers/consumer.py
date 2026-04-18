import json
import signal
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
    stop = {"value": False}

    def _stop_handler(_signum, _frame):
        stop["value"] = True

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    while not stop["value"]:
        run_once()
        time.sleep(poll_seconds)
