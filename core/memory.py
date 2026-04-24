from threading import Lock

_memory = []
_memory_lock = Lock()


def store_event(event):
    with _memory_lock:
        _memory.append(event)


def clear_memory():
    with _memory_lock:
        _memory.clear()


def get_memory():
    with _memory_lock:
        return list(_memory)
