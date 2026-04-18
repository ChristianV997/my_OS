import importlib

from backend.integrations import meta_ads_client, shopify_client


def test_meta_ads_fallback_without_credentials(monkeypatch):
    monkeypatch.setattr(meta_ads_client, "ACCESS_TOKEN", None)
    monkeypatch.setattr(meta_ads_client, "AD_ACCOUNT_ID", None)
    data = meta_ads_client.get_ad_spend(last_n_minutes=10)
    assert data["total_spend"] >= 0
    assert len(data["campaigns"]) > 0


def test_shopify_fallback_without_sdk(monkeypatch):
    monkeypatch.setattr(shopify_client, "shopify", None)
    monkeypatch.setattr(shopify_client, "SHOP_URL", "example.myshopify.com")
    monkeypatch.setattr(shopify_client, "ACCESS_TOKEN", "token")
    orders = shopify_client.get_orders(last_n_minutes=10)
    assert len(orders) > 0


def test_package_import_chain_resolves():
    modules = [
        "backend",
        "backend.learning",
        "backend.causal",
        "backend.agents",
        "backend.decision",
        "backend.data",
        "backend.regime",
        "backend.monitoring",
        "backend.simulation",
        "backend.integrations",
        "agents",
        "scripts",
        "tests",
    ]
    for module in modules:
        assert importlib.import_module(module) is not None
