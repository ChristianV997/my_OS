import json
import os
import time
from collections import defaultdict

META_PATH = "backend/ci/meta_metrics.json"
EMA_ALPHA = 0.2
STAGNATION_WINDOW = 5
STAGNATION_THRESHOLD = 0.01


def _now():
    return int(time.time())


def load_meta():
    if not os.path.exists(META_PATH):
        return {"regimes": {}, "transitions": [], "last_regime": None}
    with open(META_PATH, "r") as f:
        return json.load(f)


def save_meta(meta):
    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)


def ema(old, new):
    if old is None:
        return new
    return old * (1 - EMA_ALPHA) + new * EMA_ALPHA


def update_transition(meta, regime):
    last = meta.get("last_regime")
    if last != regime:
        meta["transitions"].append({"from": last, "to": regime, "ts": _now()})
        meta["last_regime"] = regime


def update_regime_stats(meta, regime, metrics):
    r = meta["regimes"].setdefault(regime, {
        "ema": {},
        "history": [],
        "improvement_rate": 0.0,
        "stagnating": False
    })

    # EMA update per metric
    for k, v in metrics.items():
        prev = r["ema"].get(k)
        r["ema"][k] = ema(prev, v)

    # Append short history (bounded)
    r["history"].append({"ts": _now(), **metrics})
    if len(r["history"]) > 50:
        r["history"] = r["history"][-50:]

    # Compute improvement rate (slope of avg_roas over recent window)
    hist = r["history"][-STAGNATION_WINDOW:]
    if len(hist) >= 3:
        xs = list(range(len(hist)))
        ys = [h.get("avg_roas", 0.0) for h in hist]
        # simple slope
        x_mean = sum(xs) / len(xs)
        y_mean = sum(ys) / len(ys)
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        den = sum((x - x_mean) ** 2 for x in xs) or 1e-6
        slope = num / den
        r["improvement_rate"] = slope
        r["stagnating"] = abs(slope) < STAGNATION_THRESHOLD
    else:
        r["improvement_rate"] = 0.0
        r["stagnating"] = False


def get_regime_status(meta, regime):
    r = meta.get("regimes", {}).get(regime)
    if not r:
        return {"stagnating": False, "improvement_rate": 0.0}
    return {
        "stagnating": r.get("stagnating", False),
        "improvement_rate": r.get("improvement_rate", 0.0)
    }


def adjust_evolution_params(evolution_engine, regime_status):
    # soft hooks: if attributes exist, adjust; otherwise no-op
    if not regime_status.get("stagnating"):
        return

    # Increase exploration / mutation when stagnating
    if hasattr(evolution_engine, "mutation_boost"):
        evolution_engine.mutation_boost = min(2.0, getattr(evolution_engine, "mutation_boost", 1.0) * 1.2)

    if hasattr(evolution_engine, "exploration_rate"):
        evolution_engine.exploration_rate = min(1.0, getattr(evolution_engine, "exploration_rate", 0.2) * 1.2)


def step(meta, regime, metrics, evolution_engine=None):
    update_transition(meta, regime)
    update_regime_stats(meta, regime, metrics)
    status = get_regime_status(meta, regime)
    if evolution_engine is not None:
        adjust_evolution_params(evolution_engine, status)
    return meta, status
