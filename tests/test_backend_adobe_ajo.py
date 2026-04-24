"""Tests for backend/integrations/adobe_ajo.py"""
import backend.integrations.adobe_ajo as ajo


def test_is_configured_no_token(monkeypatch):
    monkeypatch.setattr(ajo, "_AJO_TOKEN", "")
    assert ajo.is_configured() is False


def test_is_configured_with_token(monkeypatch):
    monkeypatch.setattr(ajo, "_AJO_TOKEN", "tok123")
    assert ajo.is_configured() is True


def test_pause_campaign_stub(monkeypatch):
    monkeypatch.setattr(ajo, "_AJO_TOKEN", "")
    result = ajo.pause_campaign("camp-001")
    assert result["status"] == "paused_mock"
    assert result["campaign_id"] == "camp-001"


def test_scale_campaign_stub(monkeypatch):
    monkeypatch.setattr(ajo, "_AJO_TOKEN", "")
    result = ajo.scale_campaign("camp-001", 2.0)
    assert result["status"] == "scaled_mock"
    assert result["campaign_id"] == "camp-001"
    assert result["budget_multiplier"] == 2.0


def test_scale_campaign_default_multiplier(monkeypatch):
    monkeypatch.setattr(ajo, "_AJO_TOKEN", "")
    result = ajo.scale_campaign("camp-002")
    assert result["budget_multiplier"] == 1.5


def test_pause_no_requests(monkeypatch):
    monkeypatch.setattr(ajo, "_AJO_TOKEN", "tok123")
    monkeypatch.setattr(ajo, "_requests", None)
    result = ajo.pause_campaign("camp-003")
    assert result["status"] == "paused_mock"


def test_scale_no_requests(monkeypatch):
    monkeypatch.setattr(ajo, "_AJO_TOKEN", "tok123")
    monkeypatch.setattr(ajo, "_requests", None)
    result = ajo.scale_campaign("camp-004", 3.0)
    assert result["status"] == "scaled_mock"
