from backend.integrations import shopify_client
from backend.integrations import meta_ads_client
from backend.core.state import ensure_state_shape
from backend.core.system_v5 import SystemV5
from backend.decision.engine import decide


def test_shopify_orders_fallback_without_credentials(monkeypatch):
    monkeypatch.setattr(shopify_client, "SHOP_URL", None)
    monkeypatch.setattr(shopify_client, "ACCESS_TOKEN", None)
    orders = shopify_client.get_orders(last_n_minutes=10)
    assert len(orders) > 0
    assert "total_price" in orders[0]


def test_meta_ads_fallback_without_credentials(monkeypatch):
    monkeypatch.setattr(meta_ads_client, "ACCESS_TOKEN", None)
    monkeypatch.setattr(meta_ads_client, "AD_ACCOUNT_ID", None)
    ads = meta_ads_client.get_ad_spend(last_n_days=1)
    assert ads["total_spend"] > 0
    assert len(ads["campaigns"]) > 0
    assert [c["campaign_id"] for c in ads["campaigns"]] == ["camp_1", "camp_2", "camp_3"]


def test_meta_ads_fallback_without_requests(monkeypatch):
    monkeypatch.setattr(meta_ads_client, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(meta_ads_client, "AD_ACCOUNT_ID", "account")
    monkeypatch.setattr(meta_ads_client, "requests", None)
    ads = meta_ads_client.get_ad_spend(last_n_days=1)
    assert ads["total_spend"] > 0
    assert len(ads["campaigns"]) > 0


def test_meta_ads_uses_bearer_header_and_normalized_account(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"campaign_id": "camp_1", "spend": "5.5"}]}

    class DummyRequests:
        @staticmethod
        def get(url, params=None, headers=None, timeout=10):
            captured["url"] = url
            captured["params"] = params or {}
            captured["headers"] = headers or {}
            captured["timeout"] = timeout
            return DummyResponse()

    monkeypatch.setattr(meta_ads_client, "ACCESS_TOKEN", "token-123")
    monkeypatch.setattr(meta_ads_client, "AD_ACCOUNT_ID", "act_123")
    monkeypatch.setattr(meta_ads_client, "requests", DummyRequests)

    ads = meta_ads_client.get_ad_spend(last_n_days=1)
    assert ads["total_spend"] == 5.5
    assert "access_token" not in captured["params"]
    assert captured["headers"].get("Authorization") == "Bearer token-123"
    assert "/act_123/" in captured["url"]
    assert "act_act_" not in captured["url"]


def test_ensure_state_shape_backfills_legacy_state():
    class LegacyState:
        pass

    state = ensure_state_shape(LegacyState())
    assert hasattr(state, "event_log")
    assert hasattr(state.event_log, "rows")
    assert hasattr(state, "graph")
    assert hasattr(state.graph, "edges")
    assert hasattr(state, "capital")
    assert hasattr(state, "memory")


def test_decide_handles_legacy_state_shape():
    class LegacyState:
        pass

    decisions = decide(LegacyState())
    assert isinstance(decisions, list)
    assert len(decisions) > 0


def test_system_v5_smoke_cycle():
    class DummyEnv:
        def execute(self, action):
            return {"roas": 1.0, "revenue": 100.0, "orders": 1, "cost": 50.0}

    system = SystemV5()
    for _ in range(3):
        results = system.run_cycle(DummyEnv(), decide)

    assert len(results) > 0
    assert all("prediction" in row for row in results)
    assert len(system.state.event_log.rows) > 0
