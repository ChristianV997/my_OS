"""Tests for the simulation layer (simulation/ package)."""
import math
import pytest


# ── feature extraction ────────────────────────────────────────────────────────

def test_feature_vector_length():
    from simulation.features import extract, FEATURE_NAMES
    sig = {"product": "sneakers", "score": 0.8, "velocity": 0.3}
    fv = extract(sig)
    assert len(fv) == len(FEATURE_NAMES)


def test_feature_bias_is_one():
    from simulation.features import extract
    sig = {"product": "sneakers", "score": 0.5}
    fv = extract(sig)
    assert fv[-1] == 1.0  # bias term always 1


def test_feature_uses_patterns():
    from simulation.features import extract
    sig = {"product": "x", "score": 0.5, "hook": "urgency"}
    patterns = {"hook_scores": {"urgency": 0.9}, "angle_scores": {}, "regime_scores": {}}
    fv = extract(sig, patterns=patterns)
    # hook_score is index 2
    assert fv[2] == pytest.approx(0.9)


def test_feature_history_win_rate():
    from simulation.features import extract
    history = [{"roas": 2.0, "ctr": 0.03, "cvr": 0.02, "label": "WINNER"}] * 5 + \
              [{"roas": 0.5, "ctr": 0.005, "cvr": 0.005, "label": "LOSER"}] * 5
    sig = {"product": "shoes", "score": 0.5}
    fv = extract(sig, history=history)
    # hist_win_rate is index 11
    assert fv[11] == pytest.approx(0.5)


def test_batch_extract_length_matches():
    from simulation.features import batch_extract
    signals = [{"product": f"p{i}", "score": 0.5} for i in range(7)]
    result = batch_extract(signals)
    assert len(result) == 7


# ── scoring model ─────────────────────────────────────────────────────────────

def test_scoring_model_heuristic_before_fit():
    from simulation.model import ScoringModel
    m = ScoringModel()
    assert not m.is_fitted
    scores = m.predict([{"product": "shoes", "score": 0.7}])
    assert len(scores) == 1
    assert 0.0 <= scores[0] <= 1.0


def test_scoring_model_fits_and_predicts():
    from simulation.model import ScoringModel
    m = ScoringModel()
    rows = [
        {"product": "shoes", "roas": 2.0, "ctr": 0.03, "cvr": 0.02,
         "hook": "urgency", "angle": "price", "env_regime": "bull", "label": "WINNER"}
        for _ in range(25)
    ]
    ok = m.fit(rows)
    assert ok is True
    assert m.is_fitted
    scores = m.predict([{"product": "shoes", "score": 0.7}])
    assert len(scores) == 1
    assert 0.0 <= scores[0] <= 1.0


def test_scoring_model_skips_fit_on_insufficient_data():
    from simulation.model import ScoringModel
    m = ScoringModel()
    rows = [{"product": "x", "roas": 1.0, "ctr": 0.02, "cvr": 0.01}] * 5
    ok = m.fit(rows)
    assert ok is False


# ── calibrator ────────────────────────────────────────────────────────────────

def test_calibrator_record_and_correct():
    from simulation.calibrator import SimulationCalibrator
    cal = SimulationCalibrator()
    for _ in range(10):
        cal.record("shoes", predicted_roas=2.0, actual_roas=1.5)
    corrected = cal.correct("shoes", 2.0)
    # bias ≈ 0.5, so corrected should be < 2.0
    assert corrected < 2.0


def test_calibrator_falls_back_to_global():
    from simulation.calibrator import SimulationCalibrator
    cal = SimulationCalibrator()
    # Only 1 product update → below MIN_UPDATES threshold → uses global
    cal.record("unknown_product", 1.0, 0.8)
    result = cal.correct("unknown_product", 1.5)
    assert isinstance(result, float)


def test_calibrator_report_has_required_keys():
    from simulation.calibrator import SimulationCalibrator
    cal = SimulationCalibrator()
    report = cal.report()
    assert "bias_mean" in report
    assert "rmse" in report
    assert "total_updates" in report
    assert "ready" in report


# ── replay store ─────────────────────────────────────────────────────────────

def test_replay_store_ingest_and_count():
    from simulation.replay import ReplayStore
    store = ReplayStore()
    rows = [{"product": "shoes", "roas": 1.8, "ctr": 0.025, "label": "WINNER"}] * 10
    n = store.ingest(rows)
    assert n == 10
    assert store.row_count() == 10


def test_replay_store_product_history():
    from simulation.replay import ReplayStore
    store = ReplayStore()
    store.ingest([{"product": "hat", "roas": 1.2, "ctr": 0.02, "label": "NEUTRAL"}] * 5)
    hist = store.product_history("hat")
    assert len(hist) == 5


def test_replay_store_hook_stats():
    from simulation.replay import ReplayStore
    store = ReplayStore()
    store.ingest([
        {"product": "shoes", "hook": "urgency", "roas": 2.0, "ctr": 0.03,
         "eng_score": 0.8, "label": "WINNER"},
        {"product": "shoes", "hook": "social_proof", "roas": 1.0, "ctr": 0.015,
         "eng_score": 0.4, "label": "NEUTRAL"},
    ])
    stats = store.hook_stats(top_n=5)
    hooks = [s["hook"] for s in stats]
    assert "urgency" in hooks


# ── ranking ───────────────────────────────────────────────────────────────────

def test_ranking_assigns_rank_1_to_highest_score():
    from simulation.ranking import SimulationResult, rank_results
    r1 = SimulationResult(signal={}, product="a", hook="", angle="",
                          predicted_engagement=0.9)
    r2 = SimulationResult(signal={}, product="b", hook="", angle="",
                          predicted_engagement=0.3)
    ranked = rank_results([r2, r1])
    assert ranked[0].product == "a"
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2


def test_build_result_corrected_roas_nonnegative():
    from simulation.ranking import build_result
    sig = {"product": "shoes", "score": 0.7}
    result = build_result(sig, predicted_engagement=0.8)
    assert result.corrected_roas >= 0.0
    assert 0.0 <= result.confidence <= 1.0
    assert 0.0 <= result.risk_score <= 1.0


# ── engine ────────────────────────────────────────────────────────────────────

def test_engine_score_signals_returns_ranked_list():
    from simulation.engine import SimulationEngine
    engine = SimulationEngine()
    signals = [
        {"product": "shoes", "score": 0.8, "hook": "urgency"},
        {"product": "hat", "score": 0.5, "hook": "social_proof"},
    ]
    results = engine.score_signals(signals)
    assert len(results) == 2
    assert results[0].rank == 1
    assert results[1].rank == 2


def test_engine_warm_up_with_sufficient_data():
    from simulation.engine import SimulationEngine
    engine = SimulationEngine()
    rows = [
        {"product": "shoes", "roas": 1.8, "ctr": 0.03, "cvr": 0.02,
         "hook": "urgency", "angle": "price", "env_regime": "bull", "label": "WINNER"}
        for _ in range(25)
    ]
    ok = engine.warm_up(rows)
    assert ok is True
    assert engine._warmed_up


def test_engine_record_outcome_increments_count():
    from simulation.engine import SimulationEngine
    engine = SimulationEngine()
    engine.record_outcome("shoes", predicted_roas=2.0, actual_roas=1.5)
    assert engine._outcome_count == 1


def test_engine_report_has_required_keys():
    from simulation.engine import SimulationEngine
    engine = SimulationEngine()
    report = engine.report()
    assert "warmed_up" in report
    assert "score_count" in report
    assert "calibration" in report
    assert "replay_rows" in report
    assert "model" in report


def test_engine_empty_signals_returns_empty():
    from simulation.engine import SimulationEngine
    engine = SimulationEngine()
    assert engine.score_signals([]) == []


# ── integration worker ────────────────────────────────────────────────────────

def test_run_simulation_returns_status_dict():
    from simulation.integration import _run_simulation
    result = _run_simulation()
    assert "status" in result
    assert result["status"] in ("ok", "error", "skipped")
