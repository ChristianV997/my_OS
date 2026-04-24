import pytest
from core.pods import Pod, PodManager, VALID_STATUSES


@pytest.fixture(autouse=True)
def fresh_manager():
    mgr = PodManager()
    yield mgr
    mgr.clear()


def test_pod_defaults():
    pod = Pod("widget", "US", "meta")
    assert pod.status == "testing"
    assert pod.budget == 0.0
    assert pod.metrics == {"roas": 0.0, "spend": 0.0, "revenue": 0.0}
    assert pod.creatives == []
    assert pod.id


def test_pod_to_dict_keys():
    pod = Pod("widget", "US", "meta", budget=100.0)
    d = pod.to_dict()
    for key in ("id", "product", "market", "platform", "creatives", "budget", "metrics", "status"):
        assert key in d


def test_pod_manager_create_and_get(fresh_manager):
    pod = fresh_manager.create("gizmo", "EU", "tiktok", budget=200.0)
    assert pod.product == "gizmo"
    assert pod.market == "EU"
    assert pod.platform == "tiktok"
    fetched = fresh_manager.get(pod.id)
    assert fetched is pod


def test_pod_manager_list_all(fresh_manager):
    fresh_manager.create("a", "US", "meta")
    fresh_manager.create("b", "EU", "tiktok")
    pods = fresh_manager.list_all()
    assert len(pods) == 2


def test_pod_manager_kill(fresh_manager):
    pod = fresh_manager.create("x", "US", "meta")
    fresh_manager.kill(pod.id)
    assert fresh_manager.get(pod.id).status == "killed"


def test_pod_manager_kill_nonexistent(fresh_manager):
    with pytest.raises(KeyError):
        fresh_manager.kill("nonexistent-id")


def test_pod_manager_update_status(fresh_manager):
    pod = fresh_manager.create("x", "US", "meta")
    fresh_manager.update(pod.id, status="scaling")
    assert fresh_manager.get(pod.id).status == "scaling"


def test_pod_manager_update_invalid_status(fresh_manager):
    pod = fresh_manager.create("x", "US", "meta")
    with pytest.raises(ValueError):
        fresh_manager.update(pod.id, status="invalid")


def test_pod_manager_update_metrics(fresh_manager):
    pod = fresh_manager.create("x", "US", "meta")
    fresh_manager.update_metrics(pod.id, roas=3.0, spend=100.0, revenue=300.0)
    assert fresh_manager.get(pod.id).metrics == {"roas": 3.0, "spend": 100.0, "revenue": 300.0}


def test_pod_manager_update_nonexistent(fresh_manager):
    with pytest.raises(KeyError):
        fresh_manager.update("no-such-pod", status="scaling")


def test_pod_manager_get_returns_none(fresh_manager):
    assert fresh_manager.get("no-such-pod") is None


def test_valid_statuses():
    assert VALID_STATUSES == {"testing", "scaling", "killed"}


def test_pod_manager_max_concurrent_pods():
    mgr = PodManager(max_concurrent_pods=2)
    mgr.create("a", "US", "meta")
    mgr.create("b", "EU", "tiktok")
    with pytest.raises(RuntimeError, match="max_concurrent_pods"):
        mgr.create("c", "US", "meta")
    mgr.clear()


def test_pod_manager_active_count():
    mgr = PodManager()
    mgr.create("a", "US", "meta")
    p2 = mgr.create("b", "EU", "tiktok")
    assert mgr.active_count() == 2
    mgr.kill(p2.id)
    assert mgr.active_count() == 1
    mgr.clear()


def test_pod_manager_killed_pod_frees_slot():
    mgr = PodManager(max_concurrent_pods=1)
    p1 = mgr.create("a", "US", "meta")
    mgr.kill(p1.id)
    # After killing, a new pod should fit within the limit
    p2 = mgr.create("b", "EU", "tiktok")
    assert p2.product == "b"
    mgr.clear()
