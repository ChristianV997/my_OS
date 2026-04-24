import os
import random

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

SHOP_URL = os.getenv("SHOPIFY_STORE_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

_HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN or "",
    "Content-Type": "application/json",
}

_FALLBACK_SHOPIFY = {
    "orders": 5,
    "revenue": 150.0,
    "conversion_proxy": 5,
}


def get_shopify_metrics():
    if not (SHOP_URL and ACCESS_TOKEN) or _requests is None:
        return dict(_FALLBACK_SHOPIFY)

    try:
        url = f"https://{SHOP_URL}/admin/api/2023-10/orders.json"
        response = _requests.get(url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        orders = data.get("orders", [])
        revenue = sum(float(o.get("total_price", 0)) for o in orders)
        order_count = len(orders)

        return {
            "orders": order_count,
            "revenue": revenue,
            "conversion_proxy": order_count,
        }
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return dict(_FALLBACK_SHOPIFY)


def get_ads_metrics():
    return {
        "ctr": random.uniform(0.01, 0.1),
        "cpc": random.uniform(0.2, 2.0),
        "spend": random.uniform(5, 20),
    }


def evaluate_performance(metrics):
    revenue = metrics.get("revenue", 0)
    spend = metrics.get("spend", 0)

    roas = revenue / max(spend, 1)

    if roas > 2:
        return "scale"
    elif spend > 10 and revenue == 0:
        return "kill"

    return "test"
