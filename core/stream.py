import json
import threading

try:  # pragma: no cover
    import redis
except Exception:  # pragma: no cover
    redis = None


STREAM = "upos_events"

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
        _r.xadd(STREAM, {"data": payload})
        return

    with _QUEUE_LOCK:
        _queue.append(("local", {"data": payload}))


def consume(group="workers", consumer="c1"):
    if _r is not None:  # pragma: no cover
        try:
            _r.xgroup_create(STREAM, group, id="0", mkstream=True)
        except Exception:
            pass
        return _r.xreadgroup(group, consumer, {STREAM: ">"}, count=10, block=1000)

    with _QUEUE_LOCK:
        if not _queue:
            return []
        messages = list(_queue)
        _queue.clear()
    return [(STREAM, messages)]
