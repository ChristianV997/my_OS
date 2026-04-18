import random
import time

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.learning.calibration_log import calibration_log
from backend.causal.update import update_causal
from backend.regime.detector import detector
from backend.regime.confidence import regime_confidence

# NEW integrations
from backend.integrations.shopify_client import get_orders, compute_metrics
from backend.integrations.meta_ads_client import get_ad_spend

store = DelayedRewardStore()


def execute(decisions, state):
    results = []

    # --- REAL DATA ---
    orders = get_orders(last_n_minutes=60)
    metrics = compute_metrics(orders)
    ads = get_ad_spend(last_n_minutes=60)

    revenue = metrics["revenue"]
    order_count = metrics["orders"]
    spend = ads["spend"]

    for d in decisions:
        action = d.get("action", {})

        roas = revenue / max(spend, 1)

        pred = d.get("pred", 1.0)
        calibration_model.update(pred, roas)

        outcome = {
            "roas": round(roas, 4),
            "revenue": round(revenue, 2),
            "orders": order_count,
            "cost": spend,
            "campaign_id": ads.get("campaign_id"),
            "window_start": ads.get("since"),
            "window_end": ads.get("until"),
            "prediction": round(pred, 4),
            "error": round(pred - roas, 4),
            "timestamp": time.time()
        }

        outcome.update(action)

        store.log(action, outcome)
        state.capital += revenue - spend

        results.append(outcome)

    return results


def process_delayed():
    for delay in [5, 10, 20]:
        ready = store.get_ready(delay)
        if ready:
            update_from_delayed(ready)


def run_cycle(state):
    decisions = decide(state)
    results = execute(decisions, state)
    state.event_log.log_batch(results)

    state = learn(state, results)
    state.graph = update_causal(state.graph, state.event_log)

    # regime detection from real signal
    prev_regime = state.detected_regime
    state.detected_regime = detector.detect(state.event_log)
    regime_confidence.update(state.detected_regime, "real_market")

    calibration_log.log(calibration_model.stats())

    process_delayed()
    state.total_cycles += 1

    return state
