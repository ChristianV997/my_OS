import time

from backend.core.state import SystemState
from backend.execution.loop import execute
from core.celery_app import celery_app

_state = SystemState()


@celery_app.task
def run_real_cycle(product):
    product = product or {}
    name = str(product.get("name", "product")).strip() or "product"
    campaign_id = f"camp_{name.lower().replace(' ', '_')[:20]}"

    action = {
        "campaign_id": campaign_id,
        "variant": product.get("hook", "auto"),
        "intensity": 1.0,
        "budget": float(product.get("budget", 50)),
        "hook": product.get("hook", "auto"),
        "angle": product.get("angle", "auto"),
        "product_name": name,
    }

    decisions = [{"action": action, "pred": 1.0, "strategy": "bridge", "campaign_id": campaign_id}]
    result = execute(decisions, _state)[0]
    result["product_name"] = name
    result["timestamp"] = time.time()
    return result
