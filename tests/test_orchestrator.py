"""Tests for orchestrator.main and its worker dispatchers."""
import pytest
from unittest.mock import patch, MagicMock


def test_run_signal_ingestion_ok():
    from orchestrator.main import _run_signal_ingestion
    with patch("core.signals.signal_engine.get", return_value=[
        {"product": "test", "score": 0.8}
    ]):
        result = _run_signal_ingestion()
    assert result["status"] == "ok"
    assert result["signals"] == 1


def test_run_signal_ingestion_error():
    from orchestrator.main import _run_signal_ingestion
    with patch("core.signals.signal_engine.get", side_effect=RuntimeError("boom")):
        result = _run_signal_ingestion()
    assert result["status"] == "error"


def test_run_feedback_collection_skips_when_no_module():
    from orchestrator.main import _run_feedback_collection
    result = _run_feedback_collection()
    assert result["status"] in ("ok", "skipped")


def test_run_scaling_skips_when_ajo_not_configured():
    from orchestrator.main import _run_scaling
    with patch("backend.integrations.adobe_ajo.is_configured", return_value=False):
        result = _run_scaling()
    assert result["status"] == "skipped"


def test_collect_metrics_returns_dict():
    from orchestrator.main import _collect_metrics
    result = _collect_metrics()
    assert "avg_roas" in result
    assert "capital" in result
    assert "win_rate" in result


def test_phase_workers_cover_all_phases():
    from orchestrator.main import _PHASE_WORKERS
    from core.system.phase_controller import Phase
    for phase in Phase:
        assert phase in _PHASE_WORKERS
        assert len(_PHASE_WORKERS[phase]) > 0
