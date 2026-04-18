from backend.integrations import shopify_client
from backend.core.system_v5 import SystemV5
from backend.decision.engine import decide


def test_shopify_orders_fallback_without_credentials(monkeypatch):
    monkeypatch.setattr(shopify_client, "SHOP_URL", None)
    monkeypatch.setattr(shopify_client, "ACCESS_TOKEN", None)
    orders = shopify_client.get_orders(last_n_minutes=10)
    assert len(orders) > 0
    assert "total_price" in orders[0]


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
