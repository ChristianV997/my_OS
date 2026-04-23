import json
import logging
import os
import signal
import time

from core.storage import store_events
from core.stream import consume

logger = logging.getLogger(__name__)


def run_once():
    events = consume()
    parsed_events = []

    for _, messages in events:
        for _, payload in messages:
            try:
                parsed = json.loads(payload["data"])
            except (TypeError, json.JSONDecodeError):
                logger.warning("Skipping malformed event payload: %r", payload)
                continue

            parsed_events.append(parsed)

    store_events(parsed_events)
    return len(parsed_events)


def run(poll_seconds=1):
    max_empty_polls = max(int(os.getenv("UPOS_CONSUMER_MAX_EMPTY_POLLS", "0")), 0)
    stop = {"value": False}
    empty_polls = 0

    def _stop_handler(_signum, _frame):
        stop["value"] = True

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    while not stop["value"]:
        stored = run_once()
        if stored == 0:
            empty_polls += 1
        else:
            empty_polls = 0
        if max_empty_polls and empty_polls >= max_empty_polls:
            logger.info("Consumer stopping after %s empty polls", empty_polls)
            break
        time.sleep(poll_seconds)
