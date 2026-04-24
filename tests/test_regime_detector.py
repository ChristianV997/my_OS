"""Tests for regime detection classification accuracy."""
import pytest
import numpy as np
from backend.regime.detector import RegimeDetector
from backend.data.event_log import EventLog


def _make_log(roas_values):
    log = EventLog()
    log.rows = [{"roas": float(v)} for v in roas_values]
    return log


@pytest.fixture
def detector():
    return RegimeDetector(window=30)


# ── edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_too_few_rows_returns_unknown(self, detector):
        log = _make_log([1.0] * 5)
        assert detector.detect(log) == "unknown"

    def test_exactly_10_rows_not_unknown(self, detector):
        log = _make_log([1.0] * 10)
        result = detector.detect(log)
        assert result != "unknown"

    def test_empty_log_returns_unknown(self, detector):
        log = EventLog()
        assert detector.detect(log) == "unknown"


# ── regime classification ─────────────────────────────────────────────────────

class TestClassification:
    def test_detects_stable_regime(self, detector):
        # very flat, low variance signal
        roas = [1.0 + 0.001 * (i % 3 - 1) for i in range(30)]
        log = _make_log(roas)
        assert detector.detect(log) == "stable"

    def test_detects_growth_regime(self, detector):
        # strong upward trend
        roas = [0.5 + 0.08 * i for i in range(30)]
        log = _make_log(roas)
        assert detector.detect(log) == "growth"

    def test_detects_decay_regime(self, detector):
        # strong downward trend
        roas = [3.0 - 0.08 * i for i in range(30)]
        log = _make_log(roas)
        assert detector.detect(log) == "decay"

    def test_detects_volatile_regime(self, detector):
        # sawtooth: large swings with zero net trend → triggers volatility
        roas = [1.0 + (0.8 if i % 2 == 0 else -0.8) for i in range(30)]
        log = _make_log(roas)
        result = detector.detect(log)
        assert result == "volatile"

    def test_returns_valid_label(self, detector):
        valid = {"stable", "growth", "decay", "volatile", "neutral", "unknown"}
        for _ in range(20):
            rng = np.random.default_rng()
            roas = list(rng.uniform(0.5, 3.0, 20))
            log = _make_log(roas)
            assert detector.detect(log) in valid


# ── window behaviour ──────────────────────────────────────────────────────────

class TestWindowBehaviour:
    def test_uses_only_last_window_rows(self):
        """Detector must ignore rows outside its window."""
        det = RegimeDetector(window=15)
        # first 15 rows: strong decay (slope < -0.02)
        decay_roas = [3.0 - 0.1 * i for i in range(15)]
        # last 15 rows: clear growth
        growth_roas = [1.0 + 0.08 * i for i in range(15)]
        log = _make_log(decay_roas + growth_roas)
        # window=15 so only growth rows should be seen
        assert det.detect(log) == "growth"

    def test_larger_window_uses_more_data(self):
        det = RegimeDetector(window=30)
        roas = [1.0] * 30
        log = _make_log(roas)
        assert det.detect(log) == "stable"


# ── consistency ───────────────────────────────────────────────────────────────

class TestConsistency:
    def test_same_data_same_result(self, detector):
        roas = [1.5 + 0.05 * i for i in range(25)]
        log = _make_log(roas)
        r1 = detector.detect(log)
        r2 = detector.detect(log)
        assert r1 == r2

    def test_growth_stronger_than_stable_threshold(self, detector):
        """A slope well above 0.02 must not return stable."""
        roas = [1.0 + 0.1 * i for i in range(20)]
        log = _make_log(roas)
        assert detector.detect(log) != "stable"

    def test_decay_stronger_than_stable_threshold(self, detector):
        """A slope well below -0.02 must not return stable."""
        roas = [3.0 - 0.1 * i for i in range(20)]
        log = _make_log(roas)
        assert detector.detect(log) != "stable"


# ── macro override ────────────────────────────────────────────────────────────

class TestMacroOverride:
    def test_high_vix_forces_volatile(self, detector):
        """VIX > 30 must override stable base regime."""
        roas = [1.0 + 0.001 * (i % 3 - 1) for i in range(30)]
        log = _make_log(roas)
        base = detector.detect(log)
        assert base == "stable"
        # Now pass high VIX macro signal
        result = detector.detect(log, {"vix": 35.0})
        assert result == "volatile"

    def test_negative_gdp_stable_forces_decay(self, detector):
        """Negative GDP + stable base must become decay."""
        roas = [1.0 + 0.001 * (i % 3 - 1) for i in range(30)]
        log = _make_log(roas)
        result = detector.detect(log, {"gdp_growth": -0.5})
        assert result == "decay"

    def test_negative_gdp_growth_regime_unchanged(self, detector):
        """Negative GDP does NOT override a growth base regime."""
        roas = [0.5 + 0.08 * i for i in range(30)]
        log = _make_log(roas)
        result = detector.detect(log, {"gdp_growth": -0.5})
        assert result == "growth"

    def test_no_macro_signals_unchanged(self, detector):
        """Empty macro_signals dict must not change regime."""
        roas = [0.5 + 0.08 * i for i in range(30)]
        log = _make_log(roas)
        base = detector.detect(log)
        result = detector.detect(log, {})
        assert result == base

    def test_apply_macro_override_standalone(self):
        from backend.regime.detector import apply_macro_override
        assert apply_macro_override("stable", {"vix": 31.0}) == "volatile"
        assert apply_macro_override("stable", {"gdp_growth": -1.0}) == "decay"
        assert apply_macro_override("growth", {"gdp_growth": -1.0}) == "growth"
        assert apply_macro_override("stable", {}) == "stable"
