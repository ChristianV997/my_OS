import json
import os

import backend.learning.bandit_update as bu
from backend.core.state import SystemState

STATE_PATH = "state/state.json"


def save(state, path=STATE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "capital": state.capital,
        "regime": state.regime,
        "energy": state.energy,
        "total_cycles": state.total_cycles,
        "event_log": state.event_log.rows[-2000:],
        "memory": state.memory[-500:],
        "graph_edges": {
            f"{p}|{c}": w for (p, c), w in state.graph.edges.items()
        },
        "bandit_history": bu.bandit_memory.history,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"State saved → {path} ({os.path.getsize(path):,} bytes)")


def load(path=STATE_PATH):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        d = json.load(f)

    state = SystemState()
    state.capital = d.get("capital", 1000.0)
    state.regime = d.get("regime", "neutral")
    state.energy = d.get("energy", {"fatigue": 0.1, "load": 0.2})
    state.total_cycles = d.get("total_cycles", 0)
    state.event_log.rows = d.get("event_log", [])
    state.memory = d.get("memory", [])

    for key, weight in d.get("graph_edges", {}).items():
        parts = key.split("|", 1)
        if len(parts) == 2:
            state.graph.add_edge(parts[0], parts[1], weight)

    bu.bandit_memory.history = d.get("bandit_history", {})

    return state
