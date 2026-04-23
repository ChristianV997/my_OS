from threading import Lock

memory = []
_memory_lock = Lock()


def store_event(event):
    with _memory_lock:
        memory.append(event)


def clear_memory():
    with _memory_lock:
        memory.clear()
