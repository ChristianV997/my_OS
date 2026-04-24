import uuid
from threading import Lock

VALID_STATUSES = {"testing", "scaling", "killed"}

_pods: dict = {}
_pods_lock = Lock()


class Pod:
    """Independent revenue cell — one product/market/platform combination."""

    def __init__(self, product: str, market: str, platform: str, budget: float = 0.0):
        self.id = str(uuid.uuid4())
        self.product = product
        self.market = market
        self.platform = platform
        self.creatives: list = []
        self.budget = budget
        self.metrics: dict = {"roas": 0.0, "spend": 0.0, "revenue": 0.0}
        self.status = "testing"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product": self.product,
            "market": self.market,
            "platform": self.platform,
            "creatives": self.creatives,
            "budget": self.budget,
            "metrics": self.metrics,
            "status": self.status,
        }


class PodManager:
    """Manages the lifecycle of all Pods."""

    def __init__(self, max_concurrent_pods: int = 10) -> None:
        self.max_concurrent_pods = max_concurrent_pods

    def active_count(self) -> int:
        """Return the number of non-killed pods."""
        with _pods_lock:
            return sum(1 for p in _pods.values() if p.status != "killed")

    def create(self, product: str, market: str, platform: str, budget: float = 0.0) -> Pod:
        with _pods_lock:
            active = sum(1 for p in _pods.values() if p.status != "killed")
            if active >= self.max_concurrent_pods:
                raise RuntimeError(
                    f"Cannot create pod: max_concurrent_pods ({self.max_concurrent_pods}) reached"
                )
        pod = Pod(product, market, platform, budget)
        with _pods_lock:
            _pods[pod.id] = pod
        return pod

    def get(self, pod_id: str):
        with _pods_lock:
            return _pods.get(pod_id)

    def list_all(self) -> list:
        with _pods_lock:
            return list(_pods.values())

    def update(self, pod_id: str, **kwargs) -> Pod:
        with _pods_lock:
            pod = _pods.get(pod_id)
            if pod is None:
                raise KeyError(f"Pod {pod_id} not found")
            for key, value in kwargs.items():
                if key == "status" and value not in VALID_STATUSES:
                    raise ValueError(f"Invalid status: {value}")
                setattr(pod, key, value)
        return pod

    def kill(self, pod_id: str) -> Pod:
        with _pods_lock:
            pod = _pods.get(pod_id)
            if pod is None:
                raise KeyError(f"Pod {pod_id} not found")
            pod.status = "killed"
        return pod

    def update_metrics(self, pod_id: str, roas: float, spend: float, revenue: float) -> Pod:
        with _pods_lock:
            pod = _pods.get(pod_id)
            if pod is None:
                raise KeyError(f"Pod {pod_id} not found")
            pod.metrics = {"roas": roas, "spend": spend, "revenue": revenue}
        return pod

    def clear(self) -> None:
        with _pods_lock:
            _pods.clear()


pod_manager = PodManager()
