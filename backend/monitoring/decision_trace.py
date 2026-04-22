import json
from datetime import datetime

LOG_PATH = "backend/monitoring/decision_trace.jsonl"


def log_decision_trace(trace: dict):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "world_model_score": trace.get("world_model_score"),
        "causal_score": trace.get("causal_score"),
        "velocity_bonus": trace.get("velocity_bonus"),
        "advantage": trace.get("advantage"),
        "confidence": trace.get("confidence"),
        "final_score": trace.get("final_score"),
    }

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry
