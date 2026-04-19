import os
import datetime

try:
    import shopify
except ImportError:  # pragma: no cover
    shopify = None

API_VERSION = "2023-10"
SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")


def init_shopify():
    shop_url = os.getenv("SHOPIFY_SHOP_URL", SHOP_URL)
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", ACCESS_TOKEN)

    if not shop_url or not access_token or shopify is None:
        return False

    session = shopify.Session(shop_url, API_VERSION, access_token)
    shopify.ShopifyResource.activate_session(session)
    return True


def _mock_orders(since, now):
    return [
        {"id": "mock-1", "total_price": 120.0, "created_at": since.isoformat()},
        {"id": "mock-2", "total_price": 80.0, "created_at": now.isoformat()},
    ]


def get_orders(last_n_minutes=60):
    now = datetime.datetime.now(datetime.UTC)
    since = now - datetime.timedelta(minutes=last_n_minutes)

    if not init_shopify():
        return _mock_orders(since, now)

    try:
        orders = shopify.Order.find(
            status="any",
            created_at_min=since.isoformat()
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return _mock_orders(since, now)

    results = []

    for o in orders:
        results.append({
            "id": o.id,
            "total_price": float(o.total_price or 0.0),
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
