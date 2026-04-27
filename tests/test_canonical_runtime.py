"""Tests for the canonical RuntimeState + CalibrationStore + predictors."""
import time


# ── RuntimeState ──────────────────────────────────────────────────────────────

def test_runtime_state_has_all_domains():
    from backend.runtime.state import RuntimeState
    from backend.runtime.models import MetricsRecord, OrchestratorRecord
    rs = RuntimeState()
    assert hasattr(rs, "signals")
    assert hasattr(rs, "simulations")
    assert hasattr(rs, "playbooks")
    assert hasattr(rs, "workers")
    assert hasattr(rs, "decisions")
    assert hasattr(rs, "alerts")
    assert isinstance(rs.metrics, MetricsRecord)
    assert isinstance(rs.orchestrator, OrchestratorRecord)


def test_runtime_state_to_snapshot_type():
    from backend.runtime.state import RuntimeState, RuntimeSnapshot
    rs = RuntimeState()
    snap = rs.to_snapshot()
    assert isinstance(snap, RuntimeSnapshot)
    assert snap.type == "snapshot"


def test_runtime_state_to_snapshot_maps_metrics():
    from backend.runtime.state import RuntimeState
    from backend.runtime.models import MetricsRecord
    rs = RuntimeState(
        metrics=MetricsRecord(capital=750.0, avg_roas=1.8, cycle=42, phase="VALIDATE"),
    )
    snap = rs.to_snapshot()
    assert snap.capital == 750.0
    assert snap.avg_roas == 1.8
    assert snap.cycle == 42
    assert snap.phase == "VALIDATE"


def test_runtime_state_to_snapshot_maps_signals():
    from backend.runtime.state import RuntimeState
    from backend.runtime.models import SignalRecord
    rs = RuntimeState(signals=[
        SignalRecord(product="shoes", score=0.9, source="trends"),
        SignalRecord(product="hat",   score=0.5, source="trends"),
    ])
    snap = rs.to_snapshot()
    assert snap.signal_count == 2
    assert snap.top_signals[0]["product"] == "shoes"


def test_runtime_state_to_snapshot_maps_simulations():
    from backend.runtime.state import RuntimeState
    from backend.runtime.models import SimulationRecord
    rs = RuntimeState(simulations=[
        SimulationRecord(product="shoes", rank=1, corrected_roas=2.1, confidence=0.7),
    ])
    snap = rs.to_snapshot()
    assert len(snap.simulation_scores) == 1
    assert snap.simulation_scores[0]["corrected_roas"] == 2.1


def test_build_runtime_state_returns_runtime_state():
    from backend.runtime.state import build_runtime_state, RuntimeState
    from backend.core.state import SystemState
    rs = build_runtime_state(SystemState())
    assert isinstance(rs, RuntimeState)
    assert isinstance(rs.metrics.capital, float)
    assert isinstance(rs.decisions, list)
    assert isinstance(rs.workers, list)


def test_build_snapshot_still_works():
    """build_snapshot() must remain backward-compat (delegates to build_runtime_state)."""
    from backend.runtime.state import build_snapshot, RuntimeSnapshot
    from backend.core.state import SystemState
    snap = build_snapshot(SystemState())
    assert isinstance(snap, RuntimeSnapshot)
    assert snap.type == "snapshot"


def test_runtime_state_to_dict_serializable():
    import json
    from backend.runtime.state import RuntimeState
    from backend.runtime.models import MetricsRecord, SignalRecord
    rs = RuntimeState(
        metrics=MetricsRecord(capital=100.0),
        signals=[SignalRecord(product="shoes", score=0.8)],
    )
    d = rs.to_dict()
    j = json.dumps(d, default=str)
    assert '"shoes"' in j


# ── CalibrationStore ──────────────────────────────────────────────────────────

def test_calibration_store_record_direct():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    cs.record("shoes", predicted=2.0, actual=1.5)
    assert cs.total_paired == 1


def test_calibration_store_summary_keys():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    for i in range(25):
        cs.record("shoes", predicted=2.0 + i * 0.01, actual=1.5 + i * 0.01)
    s = cs.summary()
    assert "mae" in s and "rmse" in s and "bias" in s
    assert s["ready"] is True
    assert s["total_records"] == 25


def test_calibration_store_bias_positive_when_over_predicting():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    for _ in range(25):
        cs.record("shoes", predicted=3.0, actual=1.0)
    s = cs.summary()
    assert s["bias"] > 0


def test_calibration_store_is_calibrated_after_20():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    assert cs.is_calibrated() is False
    for _ in range(20):
        cs.record("shoes", predicted=1.5, actual=1.4)
    assert cs.is_calibrated() is True


def test_calibration_store_two_phase_pairing():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    cs.record_prediction("shoes", predicted_roas=2.0)
    paired = cs.record_outcome("shoes", actual_roas=1.8)
    assert paired is True
    assert cs.total_paired == 1


def test_calibration_store_no_outcome_without_prediction():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    paired = cs.record_outcome("unknown_product", actual_roas=1.5)
    assert paired is False
    assert cs.total_paired == 0


def test_calibration_store_recent_errors_returns_dicts():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    cs.record("shoes", 2.0, 1.5)
    errors = cs.recent_errors(n=5)
    assert len(errors) == 1
    assert "predicted" in errors[0]
    assert "actual" in errors[0]
    assert "error" in errors[0]


def test_calibration_store_reset():
    from simulation.calibration import CalibrationStore
    cs = CalibrationStore()
    for _ in range(5):
        cs.record("shoes", 2.0, 1.5)
    cs.reset()
    assert cs.total_paired == 0
    assert cs.summary()["total_records"] == 0


# ── Hook predictor ────────────────────────────────────────────────────────────

def test_hook_predictor_keyword_heuristic():
    from simulation.predictors.hooks import HookPredictor
    h = HookPredictor()
    # urgency keyword should score above a neutral hook
    urgent = h.score("Limited time deal today")
    neutral = h.score("product description")
    assert urgent > neutral
    assert 0.0 <= urgent <= 1.0


def test_hook_predictor_empty_returns_zero():
    from simulation.predictors.hooks import HookPredictor
    h = HookPredictor()
    assert h.score("") == 0.0


def test_hook_predictor_score_batch():
    from simulation.predictors.hooks import HookPredictor
    h = HookPredictor()
    scores = h.score_batch(["urgency deal now", "neutral text", ""])
    assert len(scores) == 3
    assert scores[2] == 0.0


# ── Niche predictor ───────────────────────────────────────────────────────────

def test_niche_predictor_score_in_range():
    from simulation.predictors.niche import NichePredictor
    n = NichePredictor()
    score = n.score("shoes", signal_score=0.8, velocity=0.5)
    assert 0.0 <= score <= 1.0


def test_niche_predictor_score_signal():
    from simulation.predictors.niche import NichePredictor
    n = NichePredictor()
    sig = {"product": "hat", "score": 0.7, "velocity": 0.3}
    score = n.score_signal(sig)
    assert 0.0 <= score <= 1.0


def test_niche_predictor_higher_signal_scores_higher():
    from simulation.predictors.niche import NichePredictor
    n = NichePredictor()
    high = n.score("shoes", signal_score=0.9, velocity=0.8)
    low  = n.score("shoes", signal_score=0.1, velocity=0.1)
    assert high > low


# ── Orchestrator retry + anomaly ──────────────────────────────────────────────

def test_with_retry_returns_ok_on_success():
    from orchestrator.main import _with_retry
    def good_worker():
        return {"status": "ok", "cycles": 1}
    result = _with_retry(good_worker)
    assert result["status"] == "ok"


def test_with_retry_returns_skipped_without_retrying():
    call_count = [0]
    def skipped_worker():
        call_count[0] += 1
        return {"status": "skipped", "reason": "no_events"}
    from orchestrator.main import _with_retry
    result = _with_retry(skipped_worker)
    assert result["status"] == "skipped"
    assert call_count[0] == 1   # no retry on skipped


def test_with_retry_retries_on_error():
    call_count = [0]
    def flaky_worker():
        call_count[0] += 1
        if call_count[0] < 2:
            return {"status": "error", "error": "transient"}
        return {"status": "ok"}
    from orchestrator.main import _with_retry
    result = _with_retry(flaky_worker, attempts=2)
    assert result["status"] == "ok"
    assert call_count[0] == 2


def test_with_retry_returns_error_after_exhausting_attempts():
    from orchestrator.main import _with_retry
    def always_fails():
        return {"status": "error", "error": "persistent"}
    result = _with_retry(always_fails, attempts=2)
    assert result["status"] == "error"
