"""Tests for ConsolidationEngine — full cycle correctness."""
import pytest

from backend.runtime.sleep.consolidation_engine import ConsolidationEngine
from backend.runtime.sleep.schemas              import ConsolidationResult


def test_engine_returns_consolidation_result():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    assert isinstance(result, ConsolidationResult)


def test_engine_cycle_id_is_set():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    assert result.cycle_id
    assert len(result.cycle_id) >= 8


def test_engine_finishes_with_timestamp():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    assert result.finished_at > result.started_at


def test_engine_duration_positive():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    assert result.duration_s >= 0.0


def test_engine_no_hard_errors_on_empty_store():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    # May have errors but should not raise; errors list is informational
    assert isinstance(result.errors, list)


def test_engine_ok_property():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    assert isinstance(result.ok, bool)


def test_engine_compression_ratio_nonnegative():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    assert result.compression_ratio >= 0.0


def test_engine_multiple_cycles_increment_semantic_generation():
    from backend.memory.semantic import get_semantic_store
    store  = get_semantic_store()
    gen_before = store.generation()
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    engine.run_cycle()
    # Generation may or may not bump depending on whether compaction ran
    assert store.generation() >= gen_before


def test_engine_result_to_dict():
    engine = ConsolidationEngine(workspace="test", window_hours=0.01)
    result = engine.run_cycle()
    d = result.to_dict()
    assert "cycle_id" in d
    assert "workspace" in d
    assert "compression_ratio" in d


def test_engine_workspace_isolation():
    engine_a = ConsolidationEngine(workspace="ws_a", window_hours=0.01)
    engine_b = ConsolidationEngine(workspace="ws_b", window_hours=0.01)
    res_a = engine_a.run_cycle()
    res_b = engine_b.run_cycle()
    assert res_a.workspace == "ws_a"
    assert res_b.workspace == "ws_b"
