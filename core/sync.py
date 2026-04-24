try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

_SYNC_SERVER = "http://localhost:9000/sync"


def push(data, server=_SYNC_SERVER):
    if _requests is None:
        return
    try:
        _requests.post(server, json=data, timeout=2)
    except Exception:
        pass


def pull(server=_SYNC_SERVER):
    if _requests is None:
        return None
    try:
        return _requests.get(server, timeout=2).json()
    except Exception:
        return None
