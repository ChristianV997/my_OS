"""Tests for backend.runtime.state — RuntimeSnapshot serialisation."""
import json
from unittest.mock import MagicMock


def _mock_state(cycles=5, capital=1200.0, regime="growth"):
    state = MagicMock()
    state.total_cycles = cycles
    state.capital = capital
    state.detected_regime = regime
    rows = [{"roas": 1.8, "ctr": 0.03, "cvr": 0.02} for _ in range(10)]
    state.event_log.rows = rows
    return state


def test_snapshot_fields():
    from backend.runtime.state import build_snapshot, RuntimeSnapshot
    snap = build_snapshot(_mock_state())
    assert isinstance(snap, RuntimeSnapshot)
    assert snap.cycle == 5
    assert snap.capital == 1200.0
    assert snap.regime == "growth"
    assert 0 <= snap.avg_roas <= 10
    assert 0 <= snap.win_rate <= 1


def test_snapshot_to_dict():
    from backend.runtime.state import build_snapshot
    d = build_snapshot(_mock_state()).to_dict()
    assert "type" in d
    assert "cycle" in d
    assert "capital" in d
    assert "phase" in d


def test_snapshot_to_json_is_valid():
    from backend.runtime.state import build_snapshot
    j = build_snapshot(_mock_state()).to_json()
    parsed = json.loads(j)
    assert parsed["type"] == "snapshot"


def test_snapshot_top_signals_is_list():
    from backend.runtime.state import build_snapshot
    snap = build_snapshot(_mock_state())
    assert isinstance(snap.top_signals, list)


def test_snapshot_recent_decisions_populated():
    from backend.runtime.state import build_snapshot
    snap = build_snapshot(_mock_state(cycles=20))
    assert isinstance(snap.recent_decisions, list)
