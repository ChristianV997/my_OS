"""Tests for ReplayScheduler and replay window extraction."""
import time
import uuid
import pytest

from backend.runtime.sleep.replay_scheduler import ReplayScheduler, get_scheduler
from backend.runtime.sleep.replay_window    import extract_recent, extract_window
from backend.runtime.sleep.schemas          import ConsolidationResult


# ── ReplayScheduler ───────────────────────────────────────────────────────────

def test_scheduler_status_before_start():
    s = ReplayScheduler(enabled=False)
    status = s.status()
    assert status["enabled"] is False
    assert status["cycle_count"] == 0


def test_scheduler_run_now_returns_result():
    s = ReplayScheduler(enabled=True, window_hours=0.001, interval_s=9999)
    result = s.run_now()
    assert isinstance(result, ConsolidationResult)


def test_scheduler_cycle_count_increments():
    s = ReplayScheduler(enabled=True, window_hours=0.001, interval_s=9999)
    s.run_now()
    s.run_now()
    assert s.status()["cycle_count"] == 2


def test_scheduler_last_cycle_ts_updates():
    s      = ReplayScheduler(enabled=True, window_hours=0.001, interval_s=9999)
    before = time.time()
    s.run_now()
    assert s.status()["last_cycle_ts"] >= before


def test_scheduler_disabled_start_is_noop():
    s = ReplayScheduler(enabled=False)
    s.start()
    assert not (s._thread and s._thread.is_alive())


def test_scheduler_start_stop():
    s = ReplayScheduler(enabled=True, interval_s=9999, window_hours=0.001)
    s.start()
    assert s._thread is not None and s._thread.is_alive()
    s.stop()
    assert not (s._thread and s._thread.is_alive())


def test_get_scheduler_singleton():
    a = get_scheduler()
    b = get_scheduler()
    assert a is b


# ── replay_window ─────────────────────────────────────────────────────────────

def test_extract_recent_returns_batch():
    from backend.runtime.sleep.schemas import ReplayBatch
    batch = extract_recent(n=10, workspace="test")
    assert isinstance(batch, ReplayBatch)
    assert batch.batch_id


def test_extract_recent_size_bounded():
    batch = extract_recent(n=5)
    assert batch.size <= 5


def test_extract_window_returns_batch():
    from backend.runtime.sleep.schemas import ReplayBatch
    batch = extract_window(window_hours=0.001)
    assert isinstance(batch, ReplayBatch)


def test_replay_batch_events_by_type(small_batch):
    decisions = small_batch.events_by_type("decision.logged")
    assert all(e["type"] == "decision.logged" for e in decisions)


def test_replay_batch_to_dict(small_batch):
    d = small_batch.to_dict()
    assert "batch_id" in d
    assert d["size"] == small_batch.size


def test_replay_batch_span(small_batch):
    assert small_batch.span_s > 0
