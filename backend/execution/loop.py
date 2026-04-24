import logging
import random

from backend.decision.engine import decide
from backend.decision.budget_allocator import allocate as budget_allocate, allocation_summary
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.learning.calibration_log import calibration_log
from backend.causal.update import update_causal
from backend.regime.detector import detector
from backend.regime.confidence import regime_confidence
from backend.core.regime_transition import detect_transition
from backend.core.state import ensure_state_shape
from backend.regime.meta_strategy import strategy_memory
from backend.agents.structural_evolution import structural_engine
from backend.agents.self_healing import self_healing_engine
from backend.simulation.reality_gap import reality_gap_engine
from agents.auto_kill import should_kill
from agents.amplifier import Amplifier
from backend.integrations.shopify_client import get_orders, compute_metrics
from backend.integrations.meta_ads_client import get_ad_spend
import backend.ci.hyperparam_meta as hp_meta

_log = logging.getLogger(__name__)
_amplifier = Amplifier()
store = DelayedRewardStore()

# Stochastic market environment — regime-driven trend with noise
ENV = {"trend": 0.0, "regime": "stable"}

# Hyperparameter meta-learning state (persisted to JSON file)
_hp_meta_state = hp_meta.load_hp_meta()
_prev_avg_roas: float | None = None

TOTAL_CYCLE_BUDGET = 500.0  # total spend per cycle, split across all decisions
TRANSITION_COOLDOWN_CYCLES = 5

# Campaigns flagged for kill (module-level; cleared on restart)
_kill_set: set[str] = set()

# Real-data state for reality gap calibration
_real_roas_cache: float | None = None
_real_data_counter: int = 0


def _simulate_environment():
    if random.random() < 0.05:
        ENV["regime"] = random.choice(["growth", "decay", "volatile", "stable"])
    if ENV["regime"] == "growth":
        ENV["trend"] += random.uniform(0.01, 0.05)
    elif ENV["regime"] == "decay":
        ENV["trend"] -= random.uniform(0.01, 0.05)
    elif ENV["regime"] == "volatile":
        ENV["trend"] += random.uniform(-0.1, 0.1)
    elif ENV["regime"] == "stable":
        ENV["trend"] *= 0.95
    ENV["trend"] = max(-1.0, min(1.0, ENV["trend"]))


def _generate_roas():
    _simulate_environment()
    base = 1.0 + ENV["trend"]
    noise = random.uniform(-0.3, 0.3)
    delayed = random.uniform(-0.1, 0.1)
    return max(0.1, base + noise + delayed)


def _population_diversity():
    from backend.agents.structural_evolution import structure_distance
    pop = structural_engine.population
    if len(pop) < 2:
        return 1.0
    dists = [structure_distance(pop[i], pop[j]) for i in range(len(pop)) for j in range(i + 1, len(pop))]
    return sum(dists) / len(dists)


def _refresh_real_roas():
    """Fetch real ROAS from Shopify/Meta every 10 calls; returns cached value."""
    global _real_roas_cache, _real_data_counter
    _real_data_counter += 1
    if _real_data_counter % 10 != 0:
        return _real_roas_cache
    try:
        orders = get_orders(last_n_minutes=60)
        meta = get_ad_spend(last_n_minutes=60)
        metrics = compute_metrics(orders)
        spend = meta.get("total_spend", 0.0)
        if spend > 0:
            _real_roas_cache = round(metrics["revenue"] / spend, 4)
    except Exception:
        pass  # keep cached value; clients already have their own fallback
    return _real_roas_cache


def execute(decisions, state):
    budgets = budget_allocate(decisions, total_budget=TOTAL_CYCLE_BUDGET)
    _log.debug(allocation_summary(decisions, budgets))

    results = []
    for i, d in enumerate(decisions):
        action = d.get("action", {})
        structure = d.get("structure")
        campaign_id = str(action.get("campaign_id", ""))

        # killed campaigns get minimum spend so they don't skew budget
        if campaign_id and campaign_id in _kill_set:
            cost = 5.0
        else:
            cost = round(budgets[i], 4)

        roas = _generate_roas()
        revenue = roas * cost
        clicks = max(1, int(cost * 2))
        impressions = max(clicks, int(clicks / 0.02))
        conversions = max(1, int(clicks * random.uniform(0.02, 0.15)))
        ctr = clicks / impressions
        cvr = conversions / clicks
        cac = cost / conversions if conversions else cost
        profit = round(revenue - cost, 2)

        pred = d.get("pred", 1.0)
        calibration_model.update(pred, roas)

        outcome = {
            "roas":          round(roas, 4),
            "roas_6h":       round(max(0.01, roas * random.uniform(0.70, 0.95)), 4),
            "roas_12h":      round(max(0.01, roas * random.uniform(0.85, 1.05)), 4),
            "roas_24h":      round(max(0.01, roas * random.uniform(0.90, 1.10)), 4),
            "revenue":       round(revenue, 2),
            "cost":          cost,
            "profit":        profit,
            "ctr":           round(ctr, 4),
            "cvr":           round(cvr, 4),
            "cac":           round(cac, 4),
            "prediction":    round(pred, 4),
            "error":         round(pred - roas, 4),
            "pred_lo":       d.get("pred_lo"),
            "pred_hi":       d.get("pred_hi"),
            "pred_width":    d.get("pred_width"),
            "interval_conf": d.get("interval_conf"),
            "env_regime":    ENV["regime"],
            "env_trend":     round(ENV["trend"], 4),
        }
        outcome.update(action)

        # structural evolution scoring
        if structure:
            structural_engine.score(structure, roas)

        # regime performance feedback
        strategy_memory.update(ENV["regime"], roas)

        # reality gap — feed real ROAS when Shopify/Meta credentials present
        reality_gap_engine.update(roas, _refresh_real_roas())

        # campaign lifecycle: flag kills for next cycle
        kill_signal = should_kill(outcome)
        outcome["kill_signal"] = kill_signal
        if kill_signal and campaign_id:
            _kill_set.add(campaign_id)

        store.log(action, outcome)
        state.capital += revenue - cost
        results.append(outcome)
    return results


def process_delayed():
    for delay in [5, 10, 20]:
        ready = store.get_ready(delay)
        if ready:
            update_from_delayed(ready)


def run_cycle(state):
    state = ensure_state_shape(state)

    if not structural_engine.population:
        structural_engine.initialize(n=5)

    try:
        decisions = decide(state)
        results = execute(decisions, state)
    except Exception:
        _log.exception("cycle execute failed")
        state.total_cycles += 1
        return state

    state.event_log.log_batch(results)

    try:
        state = learn(state, results)
    except Exception:
        _log.exception("cycle learn failed")

    try:
        state.graph = update_causal(state.graph, state.event_log)
    except Exception:
        _log.exception("cycle causal failed")

    previous_regime = state.detected_regime
    state.detected_regime = detector.detect(state.event_log)
    transition_detected = detect_transition(previous_regime, state.detected_regime)
    state.previous_regime = previous_regime
    state.transition = {
        "occurred": transition_detected,
        "from": previous_regime,
        "to": state.detected_regime,
    }

    cooldown = max(0, state.transition_cooldown)
    if transition_detected:
        cooldown = TRANSITION_COOLDOWN_CYCLES
    elif cooldown > 0:
        cooldown -= 1
    state.transition_cooldown = cooldown

    if results:
        for row in results:
            row["transition"] = state.transition
            row["transition_cooldown"] = cooldown

    regime_confidence.update(state.detected_regime, ENV["regime"])
    calibration_log.log(calibration_model.stats())

    process_delayed()

    # amplify winners from this cycle (stored in memory for next decide())
    try:
        winners = [r for r in results if r.get("roas", 0) > 1.5 and not r.get("kill_signal")]
        amplified = _amplifier.amplify(winners)
        if amplified:
            state.memory.extend(amplified[-5:])
    except Exception:
        _log.exception("cycle amplify failed")

    # structural evolution + hyperparam meta-learning every 10 cycles
    if state.total_cycles % 10 == 0 and state.total_cycles > 0:
        global _hp_meta_state, _prev_avg_roas
        try:
            structural_engine.evolve()
            avg_roas = (sum(r.get("roas", 0) for r in results) / max(len(results), 1))
            diversity = _population_diversity()
            self_healing_engine.heal(avg_roas, diversity, structural_engine)

            improvement = (avg_roas - _prev_avg_roas) if _prev_avg_roas is not None else 0.0
            _prev_avg_roas = avg_roas

            _hp_meta_state = hp_meta.step(
                _hp_meta_state,
                regime=state.detected_regime,
                improvement=improvement,
                evolution_engine=structural_engine,
            )
            hp_meta.save_hp_meta(_hp_meta_state)
        except Exception:
            _log.exception("cycle evolution failed")

    state.total_cycles += 1
    return state
