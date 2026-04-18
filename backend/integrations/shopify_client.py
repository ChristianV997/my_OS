import os
import datetime

try:
    import shopify
except Exception:
    shopify = None

SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
API_VERSION = "2023-10"
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
_mock_call_counter = 0
MOCK_DRIFT_CYCLE = 7
MOCK_DRIFT_MULTIPLIER = 3


def init_shopify():
    if shopify is None:
        raise RuntimeError("ShopifyAPI is not installed")

    if not SHOP_URL or not ACCESS_TOKEN:
        raise ValueError("Missing Shopify credentials")

    session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)


def get_orders(last_n_minutes=60):
    global _mock_call_counter
    if shopify is None or not SHOP_URL or not ACCESS_TOKEN:
        now = datetime.datetime.utcnow()
        _mock_call_counter += 1
        drift = (_mock_call_counter % MOCK_DRIFT_CYCLE) * MOCK_DRIFT_MULTIPLIER
        return [
            {
                "id": f"mock_{i}",
                "total_price": float(50 + (i * 10) + drift),
                "created_at": now.isoformat(),
            }
            for i in range(3)
        ]

    init_shopify()

    now = datetime.datetime.utcnow()
    since = now - datetime.timedelta(minutes=last_n_minutes)

    orders = shopify.Order.find(
        status="any",
        created_at_min=since.isoformat()
    )

    results = []

    for o in orders:
        results.append({
            "id": o.id,
            "total_price": float(o.total_price),
            "created_at": o.created_at
        })

    return results


def compute_metrics(orders):
    revenue = sum(o["total_price"] for o in orders)
    count = len(orders)

    return {
        "revenue": revenue,
        "orders": count
    }
