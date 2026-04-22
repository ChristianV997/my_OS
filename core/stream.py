import json
import os
import threading

try:  # pragma: no cover
    import redis
except Exception:  # pragma: no cover
    redis = None


STREAM = "upos_events"
STREAM_READ_COUNT = int(os.getenv("UPOS_STREAM_READ_COUNT", "10"))
STREAM_READ_BLOCK_MS = int(os.getenv("UPOS_STREAM_READ_BLOCK_MS", "1000"))

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
        _queue.append(("local", {"data": payload}))


def consume(group="workers", consumer="c1"):
    """
    Return stream messages as [(stream_name, [(message_id, {"data": "<json>"})])].

    Uses Redis consumer groups when Redis is available; otherwise drains
    the in-memory fallback queue with the same return shape.
    """
    if _r is not None:  # pragma: no cover
        try:
            _r.xgroup_create(STREAM, group, id="0", mkstream=True)
        except Exception:
            pass
        return _r.xreadgroup(
            group,
            consumer,
            {STREAM: ">"},
            count=STREAM_READ_COUNT,
            block=STREAM_READ_BLOCK_MS,
        )

    with _QUEUE_LOCK:
        if not _queue:
            return []
        messages = list(_queue)
        _queue.clear()
    return [(STREAM, messages)]
