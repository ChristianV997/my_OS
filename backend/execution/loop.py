import random
import time

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.learning.calibration_log import calibration_log
from backend.learning.campaign_learning import campaign_learning
from backend.decision.confidence import confidence_engine
from backend.causal.update import update_causal
from backend.regime.detector import detector
from backend.regime.confidence import regime_confidence
from backend.simulation.reality_gap import update_reality_gap
from backend.agents.self_healing_guard import guarded_self_healing
from backend.core.state import ensure_state_shape

from backend.integrations.shopify_client import get_orders, compute_metrics
from backend.integrations.meta_ads_client import get_ad_spend
from backend.agents.structural_evolution import structural_engine
from backend.agents.campaign_budget import campaign_budget_allocator
from backend.monitoring.alerting import send_slack, send_telegram
from agents.auto_kill import should_kill
from core.cac import estimate_cac
from monitoring.realtime_alerts import process_event

store = DelayedRewardStore()
ENV = {"trend": 0.0, "regime": "stable"}
SCALE_DOWN_FACTOR = 0.7
# TODO: replace with real click/impression feeds when connector ingestion is enabled end-to-end.
CLICKS_PER_DOLLAR = 2
EXPECTED_CTR = 0.02


def execute(decisions, state):
    state = ensure_state_shape(state)
    results = []

    orders = get_orders(last_n_minutes=60)
    metrics = compute_metrics(orders)
    ads = get_ad_spend(last_n_days=1)

    revenue = metrics["revenue"]
    order_count = metrics["orders"]
    campaigns = ads.get("campaigns") or [{"campaign_id": "fallback_campaign", "spend": 0.0}]

    total_spend = ads["total_spend"]
    total_revenue = revenue

    for d in decisions:
        action = d.get("action", {})
        structure = d.get("structure")

        campaign_id = action.get("campaign_id") or campaigns[0]["campaign_id"]
        campaign = next((c for c in campaigns if c["campaign_id"] == campaign_id), campaigns[0])

        campaign_spend = campaign["spend"]
        if d.get("scale_down"):
            campaign_spend *= SCALE_DOWN_FACTOR
        campaign_revenue = (campaign_spend / max(total_spend, 1)) * total_revenue

        roas = campaign_revenue / max(campaign_spend, 1)
        clicks = max(1, int(campaign_spend * CLICKS_PER_DOLLAR))
        impressions = max(clicks, int(clicks / EXPECTED_CTR))
        conversions = max(1, int(order_count * (campaign_spend / max(total_spend, 1))))
        ctr = clicks / max(impressions, 1)
        cvr = conversions / max(clicks, 1)
        cac = estimate_cac([{"spend": campaign_spend, "conversions": conversions}])
        profit = campaign_revenue - campaign_spend

        pred = d.get("pred", 1.0)
        calibration_model.update(pred, roas)
        gap, tuned_params = update_reality_gap(pred, roas)
        confidence = confidence_engine.compute(gap, pred - roas)
        state.last_reality_gap = gap
        state.last_confidence = confidence

        outcome = {
            "roas": round(roas, 4),
            "revenue": round(campaign_revenue, 2),
            "orders": order_count,
            "cost": campaign_spend,
            "profit": round(profit, 2),
            "ctr": round(ctr, 4),
            "cvr": round(cvr, 4),
            "cac": round(cac, 4),
            "campaign_id": campaign_id,
            "window_start": ads.get("since"),
            "window_end": ads.get("until"),
            "prediction": round(pred, 4),
            "error": round(pred - roas, 4),
            "reality_gap": None if gap is None else round(gap, 4),
            "confidence": round(confidence, 4),
            "tuned_params": tuned_params,
            "timestamp": time.time()
        }

        outcome.update(action)
        campaign_learning.update(action, outcome)
        campaign_budget_allocator.update(campaign_id, roas)

        # 🔥 structural learning
        if structure:
            structural_engine.score(structure, roas)

        if action.get("delayed", False):
            store.log(action, outcome)
        state.capital += campaign_revenue - campaign_spend

        results.append(outcome)

        if roas > 1.2:
            send_telegram(f"🏆 winner {campaign_id} roas={round(roas, 3)}")
            send_slack(f"🏆 winner {campaign_id} roas={round(roas, 3)}")

        if should_kill(outcome):
            outcome["killed"] = True
            send_telegram(f"🔪 killed {campaign_id} roas={round(roas, 3)} ctr={round(ctr, 4)}")
            send_slack(f"🔪 killed {campaign_id} roas={round(roas, 3)} ctr={round(ctr, 4)}")

        process_event(outcome)

    return results


def process_delayed():
    for delay in [5, 10, 20]:
        ready = store.get_ready(delay)
        if ready:
            update_from_delayed(ready)


def run_cycle(state):
    state = ensure_state_shape(state)
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

    if results:
        roas_values = [r.get("roas", 0.0) for r in results]
        variants = [r.get("variant") for r in results if "variant" in r]
        diversity = len(set(variants)) / max(len(variants), 1)
        state.last_heal_actions = guarded_self_healing.run(
            roas=sum(roas_values) / max(len(roas_values), 1),
            diversity=diversity,
            structural_engine=structural_engine,
            reality_gap=state.last_reality_gap,
            confidence=state.last_confidence,
        )
    else:
        state.last_heal_actions = []

    state.total_cycles += 1

    return state
