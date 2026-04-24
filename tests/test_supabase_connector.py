"""Tests for connectors/supabase_connector.py"""
import connectors.supabase_connector as sc


def test_is_configured_no_env(monkeypatch):
    monkeypatch.setattr(sc, "SUPABASE_URL", "")
    monkeypatch.setattr(sc, "SUPABASE_SERVICE_KEY", "")
    assert sc.is_configured() is False


def test_is_configured_with_env(monkeypatch):
    monkeypatch.setattr(sc, "SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setattr(sc, "SUPABASE_SERVICE_KEY", "secret")
    assert sc.is_configured() is True


def test_save_cycle_summary_no_credentials(monkeypatch):
    monkeypatch.setattr(sc, "SUPABASE_URL", "")
    monkeypatch.setattr(sc, "SUPABASE_SERVICE_KEY", "")
    result = sc.save_cycle_summary({"total_cycles": 1, "capital": 1000.0})
    assert result is False


def test_save_events_empty(monkeypatch):
    monkeypatch.setattr(sc, "SUPABASE_URL", "")
    monkeypatch.setattr(sc, "SUPABASE_SERVICE_KEY", "")
    result = sc.save_events([])
    assert result is True


def test_save_events_no_credentials(monkeypatch):
    monkeypatch.setattr(sc, "SUPABASE_URL", "")
    monkeypatch.setattr(sc, "SUPABASE_SERVICE_KEY", "")
    result = sc.save_events([{"roas": 1.2}])
    assert result is False


def test_save_cycle_summary_no_requests(monkeypatch):
    monkeypatch.setattr(sc, "SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setattr(sc, "SUPABASE_SERVICE_KEY", "secret")
    monkeypatch.setattr(sc, "_requests", None)
    result = sc.save_cycle_summary({"total_cycles": 5})
    assert result is False
