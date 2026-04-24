from threading import Lock

_memory = []
_memory_lock = Lock()

_pod_performance: dict = {}
_pod_lock = Lock()

_creative_performance: dict = {}
_creative_lock = Lock()

_product_history: dict = {}
_product_lock = Lock()


def store_event(event):
    with _memory_lock:
        _memory.append(event)


def clear_memory():
    with _memory_lock:
        _memory.clear()


def get_memory():
    with _memory_lock:
        return list(_memory)


# --- Pod performance history ---

def store_pod_performance(pod_id: str, metrics: dict) -> None:
    """Append a metrics snapshot for a pod (enables learning & reuse)."""
    with _pod_lock:
        _pod_performance.setdefault(pod_id, []).append(metrics)


def get_pod_performance(pod_id: str = None):
    """Return history for a specific pod, or the full dict if pod_id is None."""
    with _pod_lock:
        if pod_id is not None:
            return list(_pod_performance.get(pod_id, []))
        return {k: list(v) for k, v in _pod_performance.items()}


# --- Creative performance history ---

def store_creative_performance(creative_id: str, metrics: dict) -> None:
    """Append a metrics snapshot for a creative asset."""
    with _creative_lock:
        _creative_performance.setdefault(creative_id, []).append(metrics)


def get_creative_performance(creative_id: str = None):
    """Return history for a specific creative, or the full dict if None."""
    with _creative_lock:
        if creative_id is not None:
            return list(_creative_performance.get(creative_id, []))
        return {k: list(v) for k, v in _creative_performance.items()}


# --- Product success/failure history ---

def store_product_result(product_name: str, result: dict) -> None:
    """Record a success/failure outcome for a product."""
    with _product_lock:
        _product_history.setdefault(product_name, []).append(result)


def get_product_history(product_name: str = None):
    """Return history for a specific product, or the full dict if None."""
    with _product_lock:
        if product_name is not None:
            return list(_product_history.get(product_name, []))
        return {k: list(v) for k, v in _product_history.items()}


def clear_all() -> None:
    """Clear all in-memory stores (useful for testing)."""
    clear_memory()
    with _pod_lock:
        _pod_performance.clear()
    with _creative_lock:
        _creative_performance.clear()
    with _product_lock:
        _product_history.clear()
