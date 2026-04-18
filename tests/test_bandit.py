from backend.learning.bandit_update import BanditMemory
from backend.causal.graph import CausalGraph


def test_empty_stats():
    bm = BanditMemory()
    stats = bm.stats({"variant": 1})
    assert stats["mean"] == 0
    assert stats["var"] == 1


def test_update_and_stats():
    bm = BanditMemory()
    action = {"variant": 2}
    bm.update(action, 1.0)
    bm.update(action, 3.0)
    stats = bm.stats(action)
    assert stats["mean"] == 2.0
    assert stats["var"] == 1.0


def test_bandit_weight_grows_with_mean():
    from backend.learning.bandit_update import bandit_weight
    bm = BanditMemory()
    g = CausalGraph()
    action = {"variant": 3}
    bm.update(action, 2.0)
    bm.update(action, 2.0)
    import backend.learning.bandit_update as bu
    orig = bu.bandit_memory
    bu.bandit_memory = bm
    w = bandit_weight(action, g)
    bu.bandit_memory = orig
    assert w > 0


def test_bandit_key_stability():
    bm = BanditMemory()
    action_a = {"campaign_id": "c-1", "variant": 7}
    action_b = {"variant": 7, "campaign_id": "c-1"}

    bm.update(action_a, 1.0)
    bm.update(action_b, 3.0)

    assert len(bm.history) == 1
    assert bm.stats(action_a) == bm.stats(action_b)
