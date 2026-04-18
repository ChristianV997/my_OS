import os
import datetime
import shopify

SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
API_VERSION = "2023-10"
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")


def init_shopify():
    if not SHOP_URL or not ACCESS_TOKEN:
        raise ValueError("Missing Shopify credentials")

    session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)


def get_orders(last_n_minutes=60):
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
