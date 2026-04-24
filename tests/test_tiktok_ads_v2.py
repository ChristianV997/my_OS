"""Tests for the expanded connectors/tiktok_ads.py (Phase 2 additions)."""
import pytest
from connectors import tiktok_ads


# ------------------------------------------------------------------ helpers

def _no_creds(monkeypatch):
    monkeypatch.setattr(tiktok_ads, "ACCESS_TOKEN", None)
    monkeypatch.setattr(tiktok_ads, "ADVERTISER_ID", None)


def _no_requests(monkeypatch):
    monkeypatch.setattr(tiktok_ads, "ACCESS_TOKEN", "tok")
    monkeypatch.setattr(tiktok_ads, "ADVERTISER_ID", "adv")
    monkeypatch.setattr(tiktok_ads, "_requests", None)


# ------------------------------------------------------------------ get_metrics

def test_get_metrics_fallback_no_credentials(monkeypatch):
    _no_creds(monkeypatch)
    result = tiktok_ads.get_metrics()
    for key in ("spend", "clicks", "impressions", "conversions", "ctr", "cvr"):
        assert key in result
    assert result["spend"] > 0


def test_get_metrics_fallback_no_requests(monkeypatch):
    _no_requests(monkeypatch)
    result = tiktok_ads.get_metrics()
    assert result["spend"] > 0


def test_get_metrics_ctr_range(monkeypatch):
    _no_creds(monkeypatch)
    result = tiktok_ads.get_metrics()
    assert 0.0 <= result["ctr"] <= 1.0


def test_get_metrics_cvr_range(monkeypatch):
    _no_creds(monkeypatch)
    result = tiktok_ads.get_metrics()
    assert 0.0 <= result["cvr"] <= 1.0


# ------------------------------------------------------------------ campaign creation

def test_create_campaign_fallback_no_credentials(monkeypatch):
    _no_creds(monkeypatch)
    result = tiktok_ads.create_campaign("Test Campaign", budget=50.0)
    assert "campaign_id" in result
    assert result["status"] == "created"


def test_create_campaign_fallback_no_requests(monkeypatch):
    _no_requests(monkeypatch)
    result = tiktok_ads.create_campaign("Test Campaign")
    assert result["campaign_id"].startswith("tt_mock")


# ------------------------------------------------------------------ ad group creation

def test_create_ad_group_fallback_no_credentials(monkeypatch):
    _no_creds(monkeypatch)
    result = tiktok_ads.create_ad_group("camp_1", "Ad Group 1", budget=20.0)
    assert "adgroup_id" in result
    assert result["status"] == "created"


def test_create_ad_group_fallback_no_requests(monkeypatch):
    _no_requests(monkeypatch)
    result = tiktok_ads.create_ad_group("camp_1", "Ad Group 1")
    assert result["adgroup_id"].startswith("tt_mock")


# ------------------------------------------------------------------ ad creation

def test_create_ad_fallback_no_credentials(monkeypatch):
    _no_creds(monkeypatch)
    creative = {"headline": "Buy now", "body": "Great product", "cta": "SHOP_NOW"}
    result = tiktok_ads.create_ad("adgroup_1", creative)
    assert "ad_id" in result
    assert result["status"] == "created"


def test_create_ad_fallback_no_requests(monkeypatch):
    _no_requests(monkeypatch)
    creative = {"headline": "Buy now", "body": "Great product", "cta": "SHOP_NOW"}
    result = tiktok_ads.create_ad("adgroup_1", creative)
    assert result["ad_id"].startswith("tt_mock")


# ------------------------------------------------------------------ OAuth helpers

def test_exchange_code_for_token_fallback(monkeypatch):
    result = tiktok_ads.exchange_code_for_token("", "", "")
    assert "access_token" in result
    assert "refresh_token" in result
    assert "advertiser_ids" in result


def test_refresh_access_token_fallback():
    result = tiktok_ads.refresh_access_token("", "", "")
    assert "access_token" in result
    assert "refresh_token" in result


def test_exchange_code_no_requests(monkeypatch):
    monkeypatch.setattr(tiktok_ads, "_requests", None)
    result = tiktok_ads.exchange_code_for_token("app", "secret", "code")
    assert result["access_token"] == ""


# ------------------------------------------------------------------ existing get_ad_spend still works

def test_get_ad_spend_still_works(monkeypatch):
    _no_creds(monkeypatch)
    result = tiktok_ads.get_ad_spend(last_n_minutes=10)
    assert result["total_spend"] > 0
    assert len(result["campaigns"]) > 0
    assert result["campaigns"][0]["campaign_id"].startswith("tt_")
