"""Tests for Step 41 — Real-Time Dashboard endpoints.

Covers:
  /campaigns           — campaign performance table
  /campaigns/{id}/override — manual override
  /creatives           — creative performance
  /risk                — risk monitoring panel
  /geo                 — geo performance map
  /accounts            — account health
  /alerts              — real-time alerts
  /decisions           — decision visualization with reason field
"""
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    from backend.api import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# /campaigns
# ---------------------------------------------------------------------------


class TestCampaigns:
    def test_returns_list(self, client):
        resp = client.get("/campaigns")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_campaign_has_required_fields(self, client):
        resp = client.get("/campaigns")
        for c in resp.json():
            assert "campaign_id" in c
            assert "geo" in c
            assert "roas" in c
            assert "spend" in c
            assert "status" in c
            assert "current_budget" in c

    def test_campaign_has_ctr_cpc_conversion(self, client):
        resp = client.get("/campaigns")
        for c in resp.json():
            assert "ctr" in c
            assert "cpc" in c
            assert "conversion_rate" in c

    def test_campaign_status_values(self, client):
        resp = client.get("/campaigns")
        allowed = {"scale", "hold", "kill", "pause"}
        for c in resp.json():
            assert c["status"] in allowed

    def test_override_field_present(self, client):
        resp = client.get("/campaigns")
        for c in resp.json():
            assert "override" in c


# ---------------------------------------------------------------------------
# /campaigns/{id}/override
# ---------------------------------------------------------------------------


class TestCampaignOverride:
    def test_scale_override(self, client):
        resp = client.post("/campaigns/camp_us_001/override?action=scale")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "scale"
        assert data["overridden"] is True

    def test_kill_override(self, client):
        resp = client.post("/campaigns/camp_ca_003/override?action=kill")
        assert resp.status_code == 200
        assert resp.json()["status"] == "kill"

    def test_invalid_action_returns_400(self, client):
        resp = client.post("/campaigns/camp_us_001/override?action=explode")
        assert resp.status_code == 400

    def test_override_reflected_in_campaign_list(self, client):
        client.post("/campaigns/camp_de_005/override?action=pause")
        resp = client.get("/campaigns")
        de = next(c for c in resp.json() if c["campaign_id"] == "camp_de_005")
        assert de["status"] == "pause"
        assert de["override"] is True


# ---------------------------------------------------------------------------
# /creatives
# ---------------------------------------------------------------------------


class TestCreatives:
    def test_returns_dict(self, client):
        resp = client.get("/creatives")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_has_hooks_ranking(self, client):
        data = client.get("/creatives").json()
        assert "hooks_ranking" in data
        assert isinstance(data["hooks_ranking"], list)

    def test_hooks_have_roas(self, client):
        data = client.get("/creatives").json()
        for hook in data["hooks_ranking"]:
            assert "hook" in hook
            assert "roas" in hook

    def test_has_clip_performance(self, client):
        data = client.get("/creatives").json()
        assert "clip_performance" in data
        for clip in data["clip_performance"]:
            assert "clip_id" in clip
            assert "roas" in clip

    def test_has_sequence_performance(self, client):
        data = client.get("/creatives").json()
        assert "sequence_performance" in data
        for seq in data["sequence_performance"]:
            assert "sequence" in seq
            assert "avg_roas" in seq

    def test_has_variant_leaderboard(self, client):
        data = client.get("/creatives").json()
        assert "variant_leaderboard" in data
        assert isinstance(data["variant_leaderboard"], list)


# ---------------------------------------------------------------------------
# /risk
# ---------------------------------------------------------------------------


class TestRisk:
    def test_returns_dict(self, client):
        resp = client.get("/risk")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_has_system_health(self, client):
        data = client.get("/risk").json()
        assert data["system_health"] in {"healthy", "warning", "critical"}

    def test_has_drawdown_pct(self, client):
        data = client.get("/risk").json()
        assert "drawdown_pct" in data
        assert isinstance(data["drawdown_pct"], float)

    def test_has_alerts_list(self, client):
        data = client.get("/risk").json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_alert_has_level_and_color(self, client):
        data = client.get("/risk").json()
        for alert in data["alerts"]:
            assert "level" in alert
            assert "color" in alert
            assert "message" in alert

    def test_has_anomaly_detected(self, client):
        data = client.get("/risk").json()
        assert "anomaly_detected" in data
        assert isinstance(data["anomaly_detected"], bool)

    def test_has_avg_roas_48h(self, client):
        data = client.get("/risk").json()
        assert "avg_roas_48h" in data


# ---------------------------------------------------------------------------
# /geo
# ---------------------------------------------------------------------------


class TestGeo:
    def test_returns_list(self, client):
        resp = client.get("/geo")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_geo_has_required_fields(self, client):
        for entry in client.get("/geo").json():
            assert "country" in entry
            assert "roas" in entry
            assert "spend" in entry
            assert "status" in entry

    def test_status_values(self, client):
        allowed = {"scaling", "testing", "paused"}
        for entry in client.get("/geo").json():
            assert entry["status"] in allowed

    def test_has_revenue(self, client):
        for entry in client.get("/geo").json():
            assert "revenue" in entry


# ---------------------------------------------------------------------------
# /accounts
# ---------------------------------------------------------------------------


class TestAccounts:
    def test_returns_list(self, client):
        resp = client.get("/accounts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_account_has_required_fields(self, client):
        for acct in client.get("/accounts").json():
            assert "account_id" in acct
            assert "status" in acct
            assert "spend" in acct
            assert "risk_flags" in acct

    def test_account_status_values(self, client):
        allowed = {"warm", "scaling", "restricted"}
        for acct in client.get("/accounts").json():
            assert acct["status"] in allowed

    def test_risk_flags_is_list(self, client):
        for acct in client.get("/accounts").json():
            assert isinstance(acct["risk_flags"], list)


# ---------------------------------------------------------------------------
# /alerts
# ---------------------------------------------------------------------------


class TestAlerts:
    def test_returns_dict(self, client):
        resp = client.get("/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_has_count_and_health(self, client):
        data = client.get("/alerts").json()
        assert "count" in data
        assert "system_health" in data
        assert "alerts" in data

    def test_count_matches_alerts_length(self, client):
        data = client.get("/alerts").json()
        assert data["count"] == len(data["alerts"])

    def test_system_health_valid(self, client):
        data = client.get("/alerts").json()
        assert data["system_health"] in {"healthy", "warning", "critical"}


# ---------------------------------------------------------------------------
# /decisions (enhanced with reason field)
# ---------------------------------------------------------------------------


class TestDecisionsEnhanced:
    def test_decisions_has_reason(self, client):
        resp = client.get("/decisions")
        assert resp.status_code == 200
        for d in resp.json():
            assert "reason" in d
            assert isinstance(d["reason"], str)
            assert len(d["reason"]) > 0

    def test_reason_contains_roas_or_confidence(self, client):
        for d in client.get("/decisions").json():
            reason = d["reason"].lower()
            assert any(kw in reason for kw in ["roas", "confidence", "uncertainty", "score"])

    def test_existing_fields_still_present(self, client):
        for d in client.get("/decisions").json():
            for field in ("action", "score", "pred", "budget"):
                assert field in d
