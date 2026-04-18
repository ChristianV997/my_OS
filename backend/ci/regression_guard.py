import json
import os
import numpy as np

BASELINE_PATH = "backend/ci/baseline.json"


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


def save_baseline(metrics):
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w") as f:
        json.dump(metrics, f, indent=2)


def load_baseline():
    if not os.path.exists(BASELINE_PATH):
        return None
    with open(BASELINE_PATH, "r") as f:
        return json.load(f)


def compare_metrics(current, baseline):
    failures = []

    if baseline is None:
        return failures

    if current["avg_roas"] < baseline["avg_roas"] * 0.8:
        failures.append("ROAS dropped >20%")

    if current["prediction_error"] > baseline["prediction_error"] * 1.5:
        failures.append("Prediction error increased")

    if current["strategy_count"] < baseline["strategy_count"]:
        failures.append("Strategy count decreased")

    return failures
