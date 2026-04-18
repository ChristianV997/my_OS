import random
import time

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.learning.calibration_log import calibration_log
from backend.learning.campaign_learning import campaign_learning
from backend.causal.update import update_causal
from backend.regime.detector import detector
from backend.regime.confidence import regime_confidence

from backend.integrations.shopify_client import get_orders, compute_metrics
from backend.integrations.meta_ads_client import get_ad_spend
from backend.agents.structural_evolution import structural_engine

store = DelayedRewardStore()
ENV = {"trend": 0.0, "regime": "stable"}


def execute(decisions, state):
    results = []

    orders = get_orders(last_n_minutes=60)
    metrics = compute_metrics(orders)
    ads = get_ad_spend(last_n_minutes=60)

    revenue = metrics["revenue"]
    order_count = metrics["orders"]
    campaigns = ads.get("campaigns") or [{"campaign_id": "unknown", "spend": 0.0}]

    total_spend = ads["total_spend"]
    total_revenue = revenue

    for d in decisions:
        action = d.get("action", {})
        structure = d.get("structure")

        campaign_id = action.get("campaign_id") or campaigns[0]["campaign_id"]
        campaign = next((c for c in campaigns if c["campaign_id"] == campaign_id), campaigns[0])

        campaign_spend = campaign["spend"]
        campaign_revenue = (campaign_spend / max(total_spend, 1)) * total_revenue

        roas = campaign_revenue / max(campaign_spend, 1)

        pred = d.get("pred", 1.0)
        calibration_model.update(pred, roas)

        outcome = {
            "roas": round(roas, 4),
            "revenue": round(campaign_revenue, 2),
            "orders": order_count,
            "cost": campaign_spend,
            "campaign_id": campaign_id,
            "window_start": ads.get("since"),
            "window_end": ads.get("until"),
            "prediction": round(pred, 4),
            "error": round(pred - roas, 4),
            "timestamp": time.time()
        }

        outcome.update(action)
        campaign_learning.update(action, outcome)

        # 🔥 structural learning
        if structure:
            structural_engine.score(structure, roas)

        store.log(action, outcome)
        state.capital += campaign_revenue - campaign_spend

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

    state.detected_regime = detector.detect(state.event_log)
    regime_confidence.update(state.detected_regime, "real_market")

    calibration_log.log(calibration_model.stats())

    process_delayed()

    # 🔥 structural evolution step
    if state.total_cycles % 10 == 0:
        structural_engine.evolve()

    state.total_cycles += 1

    return state
