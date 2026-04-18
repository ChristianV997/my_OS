import time
from backend.learning.delayed_rewards import DelayedRewardStore


def test_not_ready_before_delay():
    store = DelayedRewardStore()
    store.log({"variant": 1}, {"roas": 1.2})
    ready = store.get_ready(delay=100)
    assert len(ready) == 0
    assert len(store.buffer) == 1


def test_ready_after_delay_clears_buffer():
    store = DelayedRewardStore()
    store.buffer.append({"t": time.time() - 60, "decision": {}, "outcome": {}})
    ready = store.get_ready(delay=1)
    assert len(ready) == 1
    assert len(store.buffer) == 0


def test_partial_ready():
    store = DelayedRewardStore()
    store.buffer.append({"t": time.time() - 60, "decision": {"a": 1}, "outcome": {}})
    store.buffer.append({"t": time.time() + 60, "decision": {"a": 2}, "outcome": {}})
    ready = store.get_ready(delay=1)
    assert len(ready) == 1
    assert len(store.buffer) == 1
