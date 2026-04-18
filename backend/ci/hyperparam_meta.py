import json
import os
from collections import defaultdict

META_HP_PATH = "backend/ci/hyperparams_meta.json"


def load_hp_meta():
    if not os.path.exists(META_HP_PATH):
        return {"history": [], "best": {}}
    with open(META_HP_PATH, "r") as f:
        return json.load(f)


def save_hp_meta(meta):
    os.makedirs(os.path.dirname(META_HP_PATH), exist_ok=True)
    with open(META_HP_PATH, "w") as f:
        json.dump(meta, f, indent=2)


def record(meta, regime, params, improvement):
    meta["history"].append({
        "regime": regime,
        "params": params,
        "improvement": improvement
    })
    if len(meta["history"]) > 200:
        meta["history"] = meta["history"][-200:]


def compute_best(meta):
    bucket = defaultdict(list)

    for h in meta["history"]:
        key = (h["regime"], tuple(sorted(h["params"].items())))
        bucket[key].append(h["improvement"])

    best = {}
    for (regime, params_tuple), vals in bucket.items():
        score = sum(vals) / len(vals)
        if regime not in best or score > best[regime]["score"]:
            best[regime] = {
                "params": dict(params_tuple),
                "score": score
            }

    meta["best"] = best
    return meta


def apply_best(evolution_engine, best, regime):
    if regime not in best:
        return

    params = best[regime]["params"]

    if hasattr(evolution_engine, "mutation_rate") and "mutation_rate" in params:
        evolution_engine.mutation_rate = params["mutation_rate"]

    if hasattr(evolution_engine, "exploration_rate") and "exploration_rate" in params:
        evolution_engine.exploration_rate = params["exploration_rate"]


def step(meta, regime, improvement, evolution_engine):
    params = {
        "mutation_rate": getattr(evolution_engine, "mutation_rate", 0.1),
        "exploration_rate": getattr(evolution_engine, "exploration_rate", 0.2)
    }

    record(meta, regime, params, improvement)
    meta = compute_best(meta)
    apply_best(evolution_engine, meta["best"], regime)

    return meta
