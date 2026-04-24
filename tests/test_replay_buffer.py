"""Tests for backend/learning/replay_buffer.py"""
from backend.learning.replay_buffer import ReplayBuffer, replay_buffer


def test_add_and_len():
    buf = ReplayBuffer(capacity=10)
    buf.add([1.0, 0.5], {"variant": 1}, 1.2)
    assert len(buf) == 1


def test_capacity_respected():
    buf = ReplayBuffer(capacity=5)
    for i in range(10):
        buf.add([float(i)], {"variant": i}, float(i))
    assert len(buf) == 5


def test_sample_returns_subset():
    buf = ReplayBuffer(capacity=100)
    for i in range(20):
        buf.add([float(i), 0.1], {"variant": i % 5}, float(i) * 0.1)
    samples = buf.sample(10)
    assert len(samples) == 10
    for s in samples:
        assert "state" in s
        assert "action" in s
        assert "reward" in s


def test_sample_less_than_available():
    buf = ReplayBuffer(capacity=100)
    buf.add([1.0], {}, 0.5)
    samples = buf.sample(50)
    assert len(samples) == 1


def test_sample_empty():
    buf = ReplayBuffer(capacity=100)
    assert buf.sample(5) == []


def test_is_ready():
    buf = ReplayBuffer(capacity=100)
    assert not buf.is_ready(min_size=10)
    for i in range(10):
        buf.add([float(i)], {}, 0.0)
    assert buf.is_ready(min_size=10)


def test_add_batch():
    buf = ReplayBuffer(capacity=50)
    experiences = [
        {"state": [1.0, 2.0], "action": {"variant": i}, "reward": float(i)}
        for i in range(5)
    ]
    buf.add_batch(experiences)
    assert len(buf) == 5


def test_module_singleton_is_replay_buffer():
    assert isinstance(replay_buffer, ReplayBuffer)


def test_reward_stored_as_float():
    buf = ReplayBuffer(capacity=10)
    buf.add([1.0], {}, 3)  # int passed
    sample = buf.sample(1)[0]
    assert isinstance(sample["reward"], float)
