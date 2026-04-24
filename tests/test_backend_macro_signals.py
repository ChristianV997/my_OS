"""Tests for backend/integrations/macro_signals.py"""
import backend.integrations.macro_signals as ms


def test_get_macro_signals_no_key(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    monkeypatch.setattr(ms, "_cache", None)
    signals = ms.get_macro_signals()
    assert "gdp_growth" in signals
    assert "cpi_yoy" in signals
    assert "consumer_sentiment" in signals
    assert "vix" in signals
    assert "treasury_10y" in signals
    assert "macro_risk_score" in signals


def test_fallback_values_are_numeric(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    monkeypatch.setattr(ms, "_cache", None)
    signals = ms.get_macro_signals()
    for key, val in signals.items():
        assert isinstance(val, float), f"{key} should be float, got {type(val)}"


def test_macro_risk_in_range(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    monkeypatch.setattr(ms, "_cache", None)
    signals = ms.get_macro_signals()
    risk = signals["macro_risk_score"]
    assert 0.0 <= risk <= 1.0


def test_is_configured_no_key(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    assert ms.is_configured() is False


def test_is_configured_with_key(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "abc123")
    assert ms.is_configured() is True


def test_no_requests_falls_back(monkeypatch):
    monkeypatch.setattr(ms, "FRED_API_KEY", "abc123")
    monkeypatch.setattr(ms, "_requests", None)
    monkeypatch.setattr(ms, "_cache", None)
    signals = ms.get_macro_signals()
    assert "macro_risk_score" in signals
    assert isinstance(signals["macro_risk_score"], float)


def test_macro_risk_high_vix():
    """High VIX + elevated CPI should push macro risk above 0.5."""
    signals = {"vix": 40.0, "cpi_yoy": 7.0, "consumer_sentiment": 45.0}
    risk = ms._macro_risk(signals)
    assert risk > 0.5


def test_macro_risk_low_vix():
    """Low VIX + moderate indicators should give low risk."""
    signals = {"vix": 12.0, "cpi_yoy": 2.0, "consumer_sentiment": 90.0}
    risk = ms._macro_risk(signals)
    assert risk < 0.5


def test_cache_is_used(monkeypatch):
    """Second call within TTL should return same object (cache hit)."""
    monkeypatch.setattr(ms, "FRED_API_KEY", "")
    monkeypatch.setattr(ms, "_cache", None)
    s1 = ms.get_macro_signals()
    s2 = ms.get_macro_signals()
    assert s1 is s2
