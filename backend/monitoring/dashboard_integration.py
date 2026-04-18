import json
import os
from datetime import datetime

from backend.monitoring.health_dashboard import HealthDashboard

LOG_PATH = "backend/monitoring/health_logs.jsonl"

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


dashboard = HealthDashboard()


def compute_diversity(structures):
    if not structures or len(structures) < 2:
        return 0.0
    from backend.agents.structural_evolution import structure_distance

    total = 0
    count = 0
    for i in range(len(structures)):
        for j in range(i + 1, len(structures)):
            total += structure_distance(structures[i], structures[j])
            count += 1

    return total / count if count else 0.0


def log_snapshot(summary):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        **summary
    }

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def update_dashboard(state):
    """
    state must include:
        roas
        predicted_roas
        novelty_weight
        strategies (dict or list)
        structures (list)
    """

    diversity = compute_diversity(state.get("structures", []))

    dashboard.update(
        roas=state["roas"],
        pred=state["predicted_roas"],
        actual=state["roas"],
        novelty_weight=state.get("novelty_weight", 0.0),
        strategy_count=len(state.get("strategies", [])),
        diversity=diversity
    )

    summary = dashboard.summary()

    log_snapshot(summary)

    return summary


def print_dashboard():
    dashboard.display()
