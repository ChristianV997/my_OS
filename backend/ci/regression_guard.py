import json
import os
import numpy as np

BASELINE_PATH = "backend/ci/baseline.json"
EMA_ALPHA = 0.2

REGIMES = ["growth", "volatile", "decay"]


def detect_regime(results):
    roas = [r.get("roas", 0) for r in results]
    if len(roas) < 5:
        return "volatile"

    trend = np.polyfit(range(len(roas)), roas, 1)[0]

    if trend > 0.01:
        return "growth"
    elif trend < -0.01:
        return "decay"
    else:
        return "volatile"


def compute_metrics(results):
    roas = [r.get("roas", 0) for r in results]
    preds = [r.get("prediction", 0) for r in results]

    avg_roas = float(np.mean(roas)) if roas else 0.0
    error = float(np.mean([p - r for p, r in zip(preds, roas)])) if roas else 0.0

    return {
        "avg_roas": avg_roas,
        "prediction_error": abs(error),
        "strategy_count": len(set([r.get("strategy") for r in results]))
    }


def load_baseline():
    if not os.path.exists(BASELINE_PATH):
        return {}
    with open(BASELINE_PATH, "r") as f:
        return json.load(f)


def save_baseline(baseline):
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2)


def ema_update(old, new):
    return old * (1 - EMA_ALPHA) + new * EMA_ALPHA


def update_baseline(baseline, regime, current):
    if regime not in baseline:
        baseline[regime] = current
        return baseline

    for k in current:
        baseline[regime][k] = ema_update(baseline[regime][k], current[k])

    return baseline


def compare_metrics(current, baseline, regime):
    failures = []

    if regime not in baseline:
        return failures

    ref = baseline[regime]

    if current["avg_roas"] < ref["avg_roas"] * 0.8:
        failures.append(f"ROAS drop in {regime}")

    if current["prediction_error"] > ref["prediction_error"] * 1.5:
        failures.append(f"Prediction error increase in {regime}")

    if current["strategy_count"] < ref["strategy_count"]:
        failures.append(f"Strategy count decreased in {regime}")

    return failures
