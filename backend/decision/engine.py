import os
import random

from backend.decision.scoring import causal_score
from backend.decision.confidence import confidence_engine, apply_confidence
from backend.learning.signals import roas_velocity, roas_acceleration
from backend.learning.bandit_update import bandit_weight
from backend.learning.calibration import calibration_model
from backend.simulation.reality_gap import reality_gap_engine
from backend.core.state import ensure_state_shape
from agents.world_model import world_model
from connectors.meta_ads_intel import MetaAdsIntel
from connectors.shopify_scraper import ShopifyScraper

_meta_intel = MetaAdsIntel()
_shopify_scraper = ShopifyScraper()

# Module-level caches to avoid per-decision network calls
_competition_cache: dict[str, float] = {}   # keyword → density score
_discovery_cache: list[dict] = []           # recently discovered Shopify products

_META_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
_SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")


def _refresh_competition(keyword: str) -> float:
    """Return a competition density score for *keyword* (0–1, cached)."""
    if keyword in _competition_cache:
        return _competition_cache[keyword]

    if not _META_TOKEN:
        _competition_cache[keyword] = 0.5  # neutral fallback
        return 0.5

    try:
        score = _meta_intel.competition_score(keyword, _META_TOKEN)
        density = float(score.get("density", 0.5))
    except Exception:
        density = 0.5

    _competition_cache[keyword] = density
    return density


def _refresh_products() -> list[dict]:
    """Return recently discovered products from Shopify (cached per session)."""
    global _discovery_cache
    if _discovery_cache:
        return _discovery_cache

    if not _SHOPIFY_STORE_URL:
        return []

    try:
        _discovery_cache = _shopify_scraper.fetch_products(_SHOPIFY_STORE_URL)
    except Exception:
        _discovery_cache = []

    return _discovery_cache


def _interval_confidence(preds: dict) -> float:
    widths = [preds.get(f"width_{h}", 0.6) for h in ("6h", "12h", "24h")]
    mean_width = sum(widths) / len(widths)
    return 1.0 / (1.0 + mean_width)


def decide(state):
    state = ensure_state_shape(state)
    world_model.train(state.event_log)

    history = [r.get("roas", 0) for r in state.event_log.rows[-10:]]
    vel = roas_velocity(history)
    acc = roas_acceleration(history)

    # reality-gap + calibration composite confidence (smoothed EMA)
    gap_summary = reality_gap_engine.summary()
    cal_stats = calibration_model.stats()
    system_conf = confidence_engine.compute(
        reality_gap=gap_summary.get("reality_gap"),
        calibration_error=cal_stats.get("bias"),
    )

    transition = state.transition or {}
    transition_occurred = bool(transition.get("occurred"))
    transition_cooldown = max(0, state.transition_cooldown)

    # Enrich available variants with discovered Shopify products
    products = _refresh_products()
    product_variants = list(range(1, 6))  # default variants 1-5
    if products:
        # map top product titles to variant slots for scoring diversity
        product_variants = list(range(1, len(products) + 2))[:5]

    decisions = []

    for i in range(5):
        variant = product_variants[i % len(product_variants)]
        action = {"variant": variant}

        # competition penalty: high density → lower score for this variant
        keyword = str(variant)
        competition_density = _refresh_competition(keyword)
        competition_penalty = competition_density * 0.2  # scale to ≤ 0.2

        preds = world_model.predict(action)

        weighted_pred = (
            0.5 * preds["roas_6h"] +
            0.3 * preds["roas_12h"] +
            0.2 * preds["roas_24h"]
        )

        corrected_pred = calibration_model.adjust_prediction(weighted_pred)

        c_score = causal_score(action, state.graph)
        velocity_bonus = vel + acc
        bandit_w = bandit_weight(action, state.graph)

        # three-factor confidence: calibration × interval narrowness × system health
        calib_conf = calibration_model.confidence_weight()
        interval_conf = _interval_confidence(preds)
        confidence = calib_conf * interval_conf * system_conf

        decision_row = {
            "action": action,
            "score": corrected_pred + c_score + velocity_bonus + bandit_w - competition_penalty,
            "pred": corrected_pred,
            "pred_lo": round(0.5 * preds["lo_6h"] + 0.3 * preds["lo_12h"] + 0.2 * preds["lo_24h"], 4),
            "pred_hi": round(0.5 * preds["hi_6h"] + 0.3 * preds["hi_12h"] + 0.2 * preds["hi_24h"], 4),
            "pred_width": round(0.5 * preds["width_6h"] + 0.3 * preds["width_12h"] + 0.2 * preds["width_24h"], 4),
            "interval_conf": round(interval_conf, 4),
            "system_conf": round(system_conf, 4),
            "competition_density": round(competition_density, 4),
        }
        decisions.append(
            apply_confidence(
                decision_row,
                confidence,
                transition=transition_occurred,
                cooldown=transition_cooldown,
            )
        )

    decisions.sort(key=lambda x: x["score"], reverse=True)
    return decisions
