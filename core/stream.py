import json
import os
import threading
import time

try:  # pragma: no cover
    import redis
except Exception:  # pragma: no cover
    redis = None


STREAM = "upos_events"
STREAM_READ_COUNT = int(os.getenv("UPOS_STREAM_READ_COUNT", "10"))
STREAM_READ_BLOCK_MS = int(os.getenv("UPOS_STREAM_READ_BLOCK_MS", "1000"))
STREAM_CONSUME_RETRIES = max(int(os.getenv("UPOS_STREAM_CONSUME_RETRIES", "3")), 1)
STREAM_CONSUME_BACKOFF_MS = max(int(os.getenv("UPOS_STREAM_CONSUME_BACKOFF_MS", "200")), 0)
STREAM_CONSUME_MAX_BACKOFF_MS = max(int(os.getenv("UPOS_STREAM_CONSUME_MAX_BACKOFF_MS", "2000")), 0)
STREAM_LOCAL_MAX_QUEUE = max(int(os.getenv("UPOS_STREAM_LOCAL_MAX_QUEUE", "1000")), 1)

_r = None
_queue = []
_QUEUE_LOCK = threading.Lock()

if redis is not None:  # pragma: no cover
    try:
        _r = redis.Redis(host="redis", port=6379, decode_responses=True)
        _r.ping()
    except Exception:
        _r = None


def publish(event):
    payload = json.dumps(event)
    if _r is not None:  # pragma: no cover
        try:
            _r.xadd(STREAM, {"data": payload})
            return
        except Exception:
            pass

    with _QUEUE_LOCK:
        if len(_queue) >= STREAM_LOCAL_MAX_QUEUE:
            _queue.pop(0)
        _queue.append(("local", {"data": payload}))


def consume(group="workers", consumer="c1"):
    """
    Return stream messages as [(stream_name, [(message_id, {"data": "<json>"})])].

    Uses Redis consumer groups when Redis is available; otherwise drains
    the in-memory fallback queue with the same return shape.
    """
    if _r is not None:  # pragma: no cover
        for attempt in range(STREAM_CONSUME_RETRIES):
            try:
                _r.xgroup_create(STREAM, group, id="0", mkstream=True)
            except Exception:
                pass
            try:
                return _r.xreadgroup(
                    group,
                    consumer,
                    {STREAM: ">"},
                    count=STREAM_READ_COUNT,
                    block=STREAM_READ_BLOCK_MS,
                )
            except Exception:
                if attempt == STREAM_CONSUME_RETRIES - 1:
                    return []
                exponent = min(attempt, 10)
                sleep_ms = min(STREAM_CONSUME_BACKOFF_MS * (2 ** exponent), STREAM_CONSUME_MAX_BACKOFF_MS)
                time.sleep(sleep_ms / 1000.0)

    with _QUEUE_LOCK:
        if not _queue:
            return []
        messages = list(_queue)
        _queue.clear()
    return [(STREAM, messages)]


def dependency_status():
    redis_connected = False
    if _r is not None:  # pragma: no cover
        try:
            _r.ping()
            redis_connected = True
        except Exception:
            redis_connected = False
    return {
        "stream": STREAM,
        "redis_available": redis is not None,
        "redis_connected": redis_connected,
        "fallback_mode": not redis_connected,
        "read_count": STREAM_READ_COUNT,
        "read_block_ms": STREAM_READ_BLOCK_MS,
    }
