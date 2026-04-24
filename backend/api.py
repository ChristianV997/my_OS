"""
MarketOS v4 — FastAPI backend
Serves the Replit market UI frontend.

Environment variables (set in Replit Secrets):
  PORT               Web server port (default 8000; Replit sets this automatically)
  STATE_PATH         DuckDB file (default state/state.db)
  ALLOWED_ORIGINS    Comma-separated CORS origins (default "*")
  CYCLES_PER_MINUTE  Background runner speed (default 10 → one cycle / 6 s)
"""
import json
import os
import threading
import time
from datetime import datetime, timezone

import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.core.state import SystemState
from backend.execution.loop import run_cycle
from backend.decision.engine import decide
from backend.decision.budget_allocator import allocate as budget_allocate
import backend.learning.calibration as cal
import backend.learning.bandit_update as bu
import backend.regime.confidence as rc
from backend.agents.structural_evolution import structural_engine

# ── config ────────────────────────────────────────────────────────────────────

STATE_PATH = os.getenv("STATE_PATH", "state/state.db")
_CYCLES_PER_MINUTE = max(1, int(os.getenv("CYCLES_PER_MINUTE", "10")))

# ── app ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="MarketOS v4", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── shared state ──────────────────────────────────────────────────────────────

_state = SystemState()
_lock = threading.Lock()
_bg_running = False
_started_at = time.time()
_last_cycle_at: float | None = None


# ── background runner ─────────────────────────────────────────────────────────

def _background_runner():
    global _state, _last_cycle_at
    sleep_s = 60.0 / _CYCLES_PER_MINUTE
    while _bg_running:
        new_state = run_cycle(_state)   # compute outside lock
        with _lock:
            _state = new_state
            _last_cycle_at = time.time()
        time.sleep(sleep_s)


# ── lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup():
    global _state, _bg_running
    from backend.core.serializer import load
    loaded = load(STATE_PATH)
    if loaded:
        _state = loaded

    _bg_running = True
    threading.Thread(target=_background_runner, daemon=True).start()


@app.on_event("shutdown")
async def _shutdown():
    global _bg_running
    _bg_running = False
    from backend.core.serializer import save
    try:
        save(_state, STATE_PATH)
    except Exception:
        pass


# ── helpers ───────────────────────────────────────────────────────────────────

def _roas_trend_slope(rows: list[dict], tail: int = 20) -> float:
    vals = [r.get("roas", 0) for r in rows[-tail:]]
    if len(vals) < 2:
        return 0.0
    n = len(vals)
    xs = list(range(n))
    xm = sum(xs) / n
    ym = sum(vals) / n
    num = sum((xs[i] - xm) * (vals[i] - ym) for i in range(n))
    den = sum((xs[i] - xm) ** 2 for i in range(n))
    return round(num / den, 6) if den > 1e-9 else 0.0


def _variant_avg(rows: list[dict]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for r in rows:
        v = str(r.get("variant", "?"))
        buckets.setdefault(v, []).append(float(r.get("roas", 0)))
    return {v: round(sum(vs) / len(vs), 4) for v, vs in buckets.items()}


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Replit uptime monitor / health check."""
    return {"ok": True}


@app.get("/status")
def status():
    """Lightweight status snapshot for polling."""
    uptime = round(time.time() - _started_at, 1)
    last = (
        datetime.fromtimestamp(_last_cycle_at, tz=timezone.utc).isoformat()
        if _last_cycle_at else None
    )
    return {
        "capital": round(_state.capital, 2),
        "regime": _state.regime,
        "detected_regime": _state.detected_regime,
        "energy": _state.energy,
        "event_count": len(_state.event_log.rows),
        "memory_size": len(_state.memory),
        "causal_edges": len(_state.graph.edges),
        "total_cycles": _state.total_cycles,
        "uptime_s": uptime,
        "last_cycle_at": last,
        "bg_running": _bg_running,
    }


@app.post("/cycle")
def cycle():
    """Trigger one manual cycle (useful for testing / Replit buttons)."""
    global _state, _last_cycle_at
    new_state = run_cycle(_state)
    with _lock:
        _state = new_state
        _last_cycle_at = time.time()
    return {
        "capital": round(_state.capital, 2),
        "total_cycles": _state.total_cycles,
        "event_count": len(_state.event_log.rows),
        "detected_regime": _state.detected_regime,
    }


@app.post("/runner/pause")
def pause_runner():
    """Pause the background cycle runner."""
    global _bg_running
    _bg_running = False
    return {"bg_running": False}


@app.post("/runner/resume")
def resume_runner():
    """Resume the background cycle runner if paused."""
    global _bg_running
    if not _bg_running:
        _bg_running = True
        threading.Thread(target=_background_runner, daemon=True).start()
    return {"bg_running": True}


@app.get("/decisions")
def decisions():
    """Top 5 ranked decisions with full prediction detail."""
    top = decide(_state)[:5]
    budgets = budget_allocate(top)
    result = []
    for i, d in enumerate(top):
        result.append({
            "action":     d["action"],
            "score":      round(d["score"], 4),
            "pred":       round(d.get("pred", 0), 4),
            "pred_lo":    round(d.get("pred_lo") or 0, 4),
            "pred_hi":    round(d.get("pred_hi") or 0, 4),
            "pred_width": round(d.get("pred_width") or 0, 4),
            "interval_conf": round(d.get("interval_conf") or 0, 4),
            "system_conf":   round(d.get("system_conf") or 0, 4),
            "budget":     round(budgets[i], 2),
        })
    return result


@app.get("/metrics")
def metrics():
    """Rich dashboard payload — all key metrics in one call."""
    rows = _state.event_log.rows
    recent = rows[-100:] if rows else []

    avg_roas = round(sum(r.get("roas", 0) for r in recent) / max(len(recent), 1), 4)
    slope = _roas_trend_slope(rows)
    capital_history = [
        round(_state.capital, 2)
    ]  # live capital; historical snapshots need DB

    # calibration
    cal_stats = cal.calibration_model.stats()

    # bandit rankings
    bandit_rankings = []
    for action_key, rewards in bu.bandit_memory.history.items():
        if rewards:
            bandit_rankings.append({
                "action": action_key,
                "avg_reward": round(float(np.mean(rewards)), 4),
                "count": len(rewards),
            })
    bandit_rankings.sort(key=lambda x: x["avg_reward"], reverse=True)

    # regime confidence
    reg_conf = round(rc.regime_confidence.confidence(), 4)

    # population diversity
    diversity = (
        round(structural_engine.population_diversity(), 4)
        if structural_engine.population else None
    )

    return {
        "avg_roas": avg_roas,
        "roas_trend_slope": slope,
        "capital": round(_state.capital, 2),
        "capital_gain": round(_state.capital - 1000.0, 2),
        "detected_regime": _state.detected_regime,
        "regime_confidence": reg_conf,
        "calibration": {
            "bias": round(cal_stats.get("bias", 0), 4),
            "uncertainty": round(cal_stats.get("uncertainty", 1), 4),
            "confidence_weight": round(cal.calibration_model.confidence_weight(), 4),
        },
        "variant_performance": _variant_avg(recent),
        "bandit_rankings": bandit_rankings[:5],
        "total_cycles": _state.total_cycles,
        "causal_edges": len(_state.graph.edges),
        "population_diversity": diversity,
        "event_count": len(rows),
    }


@app.get("/events")
def events(limit: int = Query(default=200, ge=1, le=1000)):
    """
    Last `limit` event-log rows for chart rendering.
    Reads from in-memory event log; columns: id, roas, prediction, error,
    cost, revenue, env_regime, env_trend, pred_width, interval_conf.
    """
    rows = _state.event_log.rows[-limit:]
    keep = {
        "roas", "prediction", "error", "cost", "revenue",
        "env_regime", "env_trend", "pred_width", "interval_conf",
        "roas_6h", "roas_12h", "roas_24h", "variant",
    }
    result = []
    for i, r in enumerate(rows):
        row = {k: v for k, v in r.items() if k in keep}
        row["idx"] = i
        result.append(row)
    return result


@app.get("/budget")
def budget():
    """Latest CVXPY budget allocation across the top 5 decisions."""
    top = decide(_state)[:5]
    budgets = budget_allocate(top)
    return [
        {
            "variant": d["action"].get("variant"),
            "budget": round(budgets[i], 2),
            "pred": round(d.get("pred", 0), 4),
            "pred_width": round(d.get("pred_width") or 0, 4),
        }
        for i, d in enumerate(top)
    ]


@app.get("/causal")
def causal():
    """Causal graph edges sorted by Granger weight."""
    return [
        {"from": p, "to": c, "weight": round(w, 4)}
        for (p, c), w in sorted(
            _state.graph.edges.items(), key=lambda x: abs(x[1]), reverse=True
        )
    ]


@app.get("/drift")
def drift():
    """Latest Evidently drift report JSON, if available."""
    for candidate in ["drift_report.json", "state/drift_report.json"]:
        if os.path.exists(candidate):
            try:
                with open(candidate) as f:
                    return json.load(f)
            except Exception:
                break
    return {"available": False}


@app.get("/memory")
def memory():
    """Last 20 learning memory rows."""
    recent = _state.memory[-20:]
    return [
        {k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()}
        for r in recent
    ]


# ── UPOS compatibility routes (optional — imported only when present) ──────────

try:
    from api.control import router as _control_router
    from api.dashboard import router as _dashboard_router
    app.include_router(_control_router, prefix="/control")
    app.include_router(_dashboard_router, prefix="/dashboard")
except ImportError:
    pass


# ── Phase 2 connector endpoints ───────────────────────────────────────────────

@app.get("/macro")
def macro():
    """Latest FRED macro signals (falls back to static stubs when key absent)."""
    from connectors.macro_signals import get_macro_signals
    try:
        return get_macro_signals()
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/portfolio")
def portfolio():
    """ROAS-weighted portfolio allocation across active product variants."""
    from backend.decision.portfolio_engine import top_products
    return top_products(n=10)


@app.get("/replay_buffer")
def replay_buffer_stats():
    """Replay buffer size and readiness."""
    from backend.learning.replay_buffer import replay_buffer as _rb
    return {
        "size": len(_rb),
        "capacity": _rb.capacity,
        "ready": _rb.is_ready(),
    }


@app.get("/bandit")
def bandit_status():
    """LinUCB contextual bandit arm registry (arm names only)."""
    from backend.learning.contextual_bandit import bandit_instance
    b = bandit_instance()
    return {"arms": b.arms, "alpha": b.alpha}


@app.post("/ajo/apply")
def ajo_apply(campaign_id: str, action: str, budget_multiplier: float = 1.5):
    """Apply a MarketOS action (pause/scale/hold) to an Adobe AJO campaign."""
    from connectors.adobe_ajo_connector import apply_decision
    return apply_decision(campaign_id, action, budget_multiplier)

