from fastapi import FastAPI
from backend.core.state import SystemState
from backend.execution.loop import run_cycle
from backend.decision.engine import decide

app = FastAPI(title="MarketOS v4")

_state = SystemState()


@app.get("/status")
def status():
    return {
        "capital": round(_state.capital, 2),
        "regime": _state.regime,
        "energy": _state.energy,
        "event_count": len(_state.event_log.rows),
        "memory_size": len(_state.memory),
        "causal_edges": len(_state.graph.edges),
    }


@app.post("/cycle")
def cycle():
    global _state
    _state = run_cycle(_state)
    return {
        "capital": round(_state.capital, 2),
        "event_count": len(_state.event_log.rows),
        "causal_edges": len(_state.graph.edges),
    }


@app.get("/decisions")
def decisions():
    top = decide(_state)[:3]
    return [{"action": d["action"], "score": round(d["score"], 4)} for d in top]


@app.get("/causal")
def causal():
    return [
        {"from": p, "to": c, "weight": round(w, 4)}
        for (p, c), w in sorted(
            _state.graph.edges.items(), key=lambda x: abs(x[1]), reverse=True
        )
    ]


@app.get("/memory")
def memory():
    recent = _state.memory[-20:]
    return [
        {k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()}
        for r in recent
    ]
