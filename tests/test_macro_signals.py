"""Tests for connectors/macro_signals.py"""
import connectors.macro_signals as ms


def test_get_macro_signals_no_key(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    signals = ms.get_macro_signals()
    # Should return fallback values
    assert "fed_funds_rate" in signals
    assert "cpi_yoy" in signals
    assert "unemployment" in signals
    assert "treasury_10y" in signals
    assert "macro_risk_score" in signals


def test_fallback_values_are_numeric(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    signals = ms.get_macro_signals()
    for key, val in signals.items():
        assert isinstance(val, float), f"{key} should be float, got {type(val)}"


def test_macro_risk_in_range(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    signals = ms.get_macro_signals()
    risk = signals["macro_risk_score"]
    assert 0.0 <= risk <= 1.0


def test_is_configured_no_key(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    assert ms.is_configured() is False


def test_is_configured_with_key(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "abc123")
    assert ms.is_configured() is True


def test_get_macro_signals_no_requests(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "abc123")
    monkeypatch.setattr(ms, "_requests", None)
    signals = ms.get_macro_signals()
    # Should still return fallback values
    assert "macro_risk_score" in signals
    assert isinstance(signals["macro_risk_score"], float)


def test_macro_risk_high_rate():
    """High interest rates should push macro risk upward."""
    signals = {"fed_funds_rate": 9.0, "cpi_yoy": 8.0, "unemployment": 8.0}
    risk = ms._macro_risk(signals)
    assert risk > 0.5


def test_macro_risk_low_rate():
    """Low rates / low inflation should give low macro risk."""
    signals = {"fed_funds_rate": 0.5, "cpi_yoy": 1.5, "unemployment": 3.5}
    risk = ms._macro_risk(signals)
    assert risk < 0.5
