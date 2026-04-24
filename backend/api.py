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

_RESEARCH_INTERVAL_S = 300  # run intelligence loop every 5 minutes
_last_research_at: float = 0.0


# ── background runner ─────────────────────────────────────────────────────────

def _research_runner():
    """Background thread: every 5 minutes extract trend keywords from recent
    events and feed them to the core intelligence discovery loop."""
    global _last_research_at
    while _bg_running:
        now = time.time()
        if now - _last_research_at >= _RESEARCH_INTERVAL_S:
            try:
                with _lock:
                    recent = list(_state.event_log.rows[-50:])
                # extract variant/product keywords from recent events
                keywords = list({
                    str(r.get("variant", ""))
                    for r in recent
                    if r.get("variant")
                })[:20]
                from core.intelligence_loop import run_intelligence
                run_intelligence(keywords)
            except Exception:
                pass
            _last_research_at = now
        time.sleep(10)


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
    threading.Thread(target=_research_runner, daemon=True).start()


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


def _cac_estimate() -> float | None:
    """Compute CAC estimate from core memory events.

    Returns None when insufficient data is available.
    """
    try:
        from core.cac import estimate_cac
        from core.memory import get_memory
        events = get_memory()
        if not events:
            # Fall back to recent event_log rows
            events = _state.event_log.rows[-100:]
        cac = estimate_cac(events)
        return round(cac, 4) if cac else None
    except Exception:
        return None


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
    """Top 5 ranked decisions with full prediction detail and human-readable reason."""
    top = decide(_state)[:5]
    budgets = budget_allocate(top)
    result = []
    for i, d in enumerate(top):
        pred = round(d.get("pred", 0), 4)
        pred_width = round(d.get("pred_width") or 0, 4)
        system_conf = round(d.get("system_conf") or 0, 4)
        interval_conf = round(d.get("interval_conf") or 0, 4)
        score = round(d["score"], 4)

        # Build human-readable decision explanation
        if pred >= 2.0 and system_conf >= 0.6 and interval_conf >= 0.6:
            reason = (
                f"Scaled: ROAS {pred} predicted with high confidence "
                f"(system={system_conf}, interval={interval_conf})"
            )
        elif pred < 1.0:
            reason = (
                f"Kill candidate: predicted ROAS {pred} below break-even "
                f"(score={score})"
            )
        elif pred_width > 1.0:
            reason = (
                f"Hold: high prediction uncertainty (width={pred_width}), "
                f"awaiting more data"
            )
        elif pred >= 1.5:
            reason = (
                f"Monitor/Scale: ROAS {pred} above threshold, "
                f"confidence={system_conf}"
            )
        else:
            reason = (
                f"Hold: moderate ROAS {pred}, insufficient confidence "
                f"(score={score})"
            )

        result.append({
            "action":        d["action"],
            "score":         score,
            "pred":          pred,
            "pred_lo":       round(d.get("pred_lo") or 0, 4),
            "pred_hi":       round(d.get("pred_hi") or 0, 4),
            "pred_width":    pred_width,
            "interval_conf": interval_conf,
            "system_conf":   system_conf,
            "budget":        round(budgets[i], 2),
            "reason":        reason,
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
        "cac_estimate": _cac_estimate(),
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
    except Exception:
        return {"error": "macro signals unavailable"}


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
    try:
        return apply_decision(campaign_id, action, budget_multiplier)
    except Exception:
        return {"error": "AJO action failed", "campaign_id": campaign_id}


# ── Step 41: Real-Time Dashboard Endpoints ────────────────────────────────────

# Window constants for event-log slicing
_RECENT_ROWS_WINDOW = 200       # general short-term window (~20 min at 6 s/cycle)
_ROWS_PER_48H = 48 * 60 * 10   # 48 h at 10 cycles/min (6 s/cycle) = 28 800 rows

# Mock data store for manual campaign overrides (in-memory)
_campaign_overrides: dict[str, str] = {}

_MOCK_CAMPAIGNS = [
    {
        "campaign_id": "camp_us_001",
        "geo": "US",
        "roas": 2.7,
        "spend": 450.0,
        "revenue": 1215.0,
        "ctr": 0.023,
        "cpc": 0.45,
        "conversion_rate": 0.031,
        "status": "scale",
        "current_budget": 500.0,
    },
    {
        "campaign_id": "camp_uk_002",
        "geo": "UK",
        "roas": 1.8,
        "spend": 220.0,
        "revenue": 396.0,
        "ctr": 0.018,
        "cpc": 0.62,
        "conversion_rate": 0.021,
        "status": "hold",
        "current_budget": 250.0,
    },
    {
        "campaign_id": "camp_ca_003",
        "geo": "CA",
        "roas": 0.8,
        "spend": 180.0,
        "revenue": 144.0,
        "ctr": 0.011,
        "cpc": 0.91,
        "conversion_rate": 0.012,
        "status": "kill",
        "current_budget": 200.0,
    },
    {
        "campaign_id": "camp_au_004",
        "geo": "AU",
        "roas": 3.1,
        "spend": 310.0,
        "revenue": 961.0,
        "ctr": 0.031,
        "cpc": 0.38,
        "conversion_rate": 0.041,
        "status": "scale",
        "current_budget": 400.0,
    },
    {
        "campaign_id": "camp_de_005",
        "geo": "DE",
        "roas": 1.4,
        "spend": 95.0,
        "revenue": 133.0,
        "ctr": 0.014,
        "cpc": 0.75,
        "conversion_rate": 0.018,
        "status": "hold",
        "current_budget": 100.0,
    },
]

_MOCK_GEO = [
    {"country": "US", "roas": 2.7, "spend": 450.0, "revenue": 1215.0, "status": "scaling"},
    {"country": "UK", "roas": 1.8, "spend": 220.0, "revenue": 396.0,  "status": "testing"},
    {"country": "CA", "roas": 0.8, "spend": 180.0, "revenue": 144.0,  "status": "paused"},
    {"country": "AU", "roas": 3.1, "spend": 310.0, "revenue": 961.0,  "status": "scaling"},
    {"country": "DE", "roas": 1.4, "spend": 95.0,  "revenue": 133.0,  "status": "testing"},
    {"country": "FR", "roas": 2.0, "spend": 140.0, "revenue": 280.0,  "status": "testing"},
]

_MOCK_ACCOUNTS = [
    {
        "account_id": "acct_001",
        "name": "Primary TikTok",
        "status": "scaling",
        "spend": 1055.0,
        "risk_flags": [],
    },
    {
        "account_id": "acct_002",
        "name": "Backup TikTok",
        "status": "warm",
        "spend": 250.0,
        "risk_flags": ["new_account"],
    },
    {
        "account_id": "acct_003",
        "name": "EU TikTok",
        "status": "restricted",
        "spend": 95.0,
        "risk_flags": ["policy_review", "spend_limited"],
    },
]

_MOCK_CREATIVES = {
    "hooks_ranking": [
        {"hook": "Stop scrolling — this changed my life", "roas": 3.2, "ctr": 0.041, "views": 48200},
        {"hook": "I was skeptical until I tried this",   "roas": 2.9, "ctr": 0.036, "views": 39100},
        {"hook": "The secret nobody tells you about",    "roas": 2.4, "ctr": 0.029, "views": 31500},
        {"hook": "POV: you finally found the solution",  "roas": 2.1, "ctr": 0.025, "views": 27800},
        {"hook": "Why are people obsessed with this?",   "roas": 1.7, "ctr": 0.019, "views": 21200},
    ],
    "clip_performance": [
        {"clip_id": "clip_001", "roas": 3.1, "spend": 210.0, "revenue": 651.0,  "views": 45000},
        {"clip_id": "clip_002", "roas": 2.7, "spend": 180.0, "revenue": 486.0,  "views": 38000},
        {"clip_id": "clip_003", "roas": 1.9, "spend": 120.0, "revenue": 228.0,  "views": 24000},
        {"clip_id": "clip_004", "roas": 0.9, "spend": 90.0,  "revenue": 81.0,   "views": 15000},
    ],
    "sequence_performance": [
        {"sequence": "hook→demo→cta",    "avg_roas": 3.0, "completion_rate": 0.72},
        {"sequence": "hook→social→cta",  "avg_roas": 2.6, "completion_rate": 0.65},
        {"sequence": "problem→solution", "avg_roas": 2.2, "completion_rate": 0.58},
    ],
    "variant_leaderboard": [],
}


@app.get("/campaigns")
def campaigns():
    """Campaign performance table with ROAS, spend, status, and geo filters."""
    rows = _state.event_log.rows
    recent = rows[-_RECENT_ROWS_WINDOW:] if rows else []

    # Enrich mock campaigns with live avg ROAS from event log if available
    live_avg_roas: float | None = (
        round(sum(r.get("roas", 0) for r in recent) / len(recent), 4)
        if recent else None
    )

    result = []
    for c in _MOCK_CAMPAIGNS:
        entry = dict(c)
        # Apply any manual overrides
        override = _campaign_overrides.get(c["campaign_id"])
        if override:
            entry["status"] = override
            entry["override"] = True
        else:
            entry["override"] = False
        # Attach live system avg_roas as a reference
        if live_avg_roas is not None:
            entry["system_avg_roas"] = live_avg_roas
        result.append(entry)

    return result


@app.post("/campaigns/{campaign_id}/override")
def campaign_override(campaign_id: str, action: str):
    """Manual override for a campaign: scale | pause | kill."""
    allowed = {"scale", "pause", "kill", "hold"}
    if action not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"action must be one of {allowed}")
    _campaign_overrides[campaign_id] = action
    return {"campaign_id": campaign_id, "status": action, "overridden": True}


@app.get("/creatives")
def creatives():
    """Creative performance: hooks ranking, clip ROAS, sequence performance, variant leaderboard."""
    rows = _state.event_log.rows
    recent = rows[-_RECENT_ROWS_WINDOW:] if rows else []

    # Build live variant leaderboard from event log
    variant_buckets: dict[str, list[float]] = {}
    for r in recent:
        v = str(r.get("variant", ""))
        if v:
            variant_buckets.setdefault(v, []).append(float(r.get("roas", 0)))
    leaderboard = sorted(
        [
            {"variant": v, "avg_roas": round(sum(vs) / len(vs), 4), "count": len(vs)}
            for v, vs in variant_buckets.items()
        ],
        key=lambda x: x["avg_roas"],
        reverse=True,
    )

    payload = dict(_MOCK_CREATIVES)
    payload["variant_leaderboard"] = leaderboard or payload["variant_leaderboard"]
    return payload


@app.get("/risk")
def risk():
    """Risk monitoring panel: alerts, drawdown, anomaly flags, system health."""
    rows = _state.event_log.rows
    recent_48h = rows[-_ROWS_PER_48H:] if rows else []

    # Drawdown from event-log capital proxy
    capital = _state.capital
    from core.risk.drawdown import DrawdownProtector
    dp = DrawdownProtector()
    for r in rows:
        rev = float(r.get("revenue", 0))
        dp.update(rev)
    drawdown_pct = round(dp.drawdown(capital), 4)

    # ROAS over last 48 h
    roas_48h_values = [float(r.get("roas", 0)) for r in recent_48h]
    avg_roas_48h = (
        round(sum(roas_48h_values) / len(roas_48h_values), 4) if roas_48h_values else 0.0
    )

    # Anomaly detection on ROAS
    from core.risk.anomaly import AnomalyDetector
    ad = AnomalyDetector()
    all_roas = [float(r.get("roas", 0)) for r in rows]
    for v in all_roas[:-1]:
        ad.update(v)
    latest_roas = all_roas[-1] if all_roas else 0.0
    is_anomaly = ad.is_anomaly(latest_roas) if all_roas else False

    alerts = []
    if drawdown_pct > 0.30:
        alerts.append({
            "level": "critical",
            "color": "red",
            "message": f"Drawdown {round(drawdown_pct * 100, 1)}% exceeds 30% threshold",
            "metric": "drawdown",
        })
    if avg_roas_48h < 1.0 and roas_48h_values:
        alerts.append({
            "level": "critical",
            "color": "red",
            "message": f"ROAS {avg_roas_48h} below 1.0 over last 48 h — review campaigns",
            "metric": "roas_48h",
        })
    if is_anomaly:
        alerts.append({
            "level": "warning",
            "color": "yellow",
            "message": f"ROAS anomaly detected: latest value {round(latest_roas, 4)}",
            "metric": "anomaly",
        })

    # System health colour
    if any(a["color"] == "red" for a in alerts):
        health = "critical"
    elif alerts:
        health = "warning"
    else:
        health = "healthy"

    return {
        "system_health": health,
        "drawdown_pct": drawdown_pct,
        "avg_roas_48h": avg_roas_48h,
        "anomaly_detected": is_anomaly,
        "alerts": alerts,
    }


@app.get("/geo")
def geo():
    """Geo performance: ROAS per country, spend distribution, expansion status."""
    rows = _state.event_log.rows
    recent = rows[-_RECENT_ROWS_WINDOW:] if rows else []

    # Compute live system-wide avg ROAS as a reference
    live_avg: float | None = (
        round(sum(r.get("roas", 0) for r in recent) / len(recent), 4)
        if recent else None
    )

    result = [dict(g) for g in _MOCK_GEO]
    if live_avg is not None:
        for entry in result:
            entry["system_avg_roas"] = live_avg
    return result


@app.get("/accounts")
def accounts():
    """Account health: status, spend per account, risk flags."""
    return list(_MOCK_ACCOUNTS)


@app.get("/alerts")
def alerts():
    """Real-time alerts across all sub-systems with severity levels."""
    # Delegate to the /risk endpoint logic and aggregate
    risk_data = risk()
    base_alerts = list(risk_data.get("alerts", []))

    # Additional alert: pacing (check capital vs expected)
    rows = _state.event_log.rows
    recent = rows[-20:] if rows else []
    if recent:
        avg_cost = sum(float(r.get("cost", r.get("spend", 0))) for r in recent) / len(recent)
        if avg_cost > 50:
            base_alerts.append({
                "level": "warning",
                "color": "yellow",
                "message": f"Pacing alert: avg cycle cost {round(avg_cost, 2)} may exceed budget",
                "metric": "pacing",
            })

    return {
        "count": len(base_alerts),
        "system_health": risk_data.get("system_health", "healthy"),
        "alerts": base_alerts,
    }


# ── Step 52: Production Hardening + Agent Hierarchy ───────────────────────────

# Module-level singletons for Step 52 features
from core.risk.global_risk_engine import global_risk_engine as _global_risk_engine
from backend.agents.agent_metrics import agent_metrics_registry as _agent_metrics
from backend.learning.world_model_calibration import world_model_calibrator as _wm_calibrator
from agents.hierarchy import ScalingAgent, GeoAgent, AudienceAgent, RiskAgent
from backend.execution.loop import TOTAL_CYCLE_BUDGET

_scaling_agent = ScalingAgent()
_geo_agent = GeoAgent()
_audience_agent = AudienceAgent()
_risk_agent = RiskAgent()


def _current_peak_capital() -> float:
    """Read the peak capital tracked by the execution loop (falls back to current capital)."""
    return getattr(_state, "_peak_capital", _state.capital)


@app.get("/agents")
def agent_performance():
    """Agent performance panel: decisions, PnL, and drift detection per agent."""
    rows = _state.event_log.rows
    recent = rows[-_RECENT_ROWS_WINDOW:] if rows else []

    # Run agents against the latest window to record live decisions
    if recent:
        avg_roas = sum(r.get("roas", 0) for r in recent) / len(recent)
        avg_ctr = sum(r.get("ctr", 0) for r in recent) / len(recent)
        avg_cvr = sum(r.get("cvr", 0) for r in recent) / len(recent)

        scaling_dec = _scaling_agent.decide({"roas": avg_roas, "current_budget": TOTAL_CYCLE_BUDGET})
        geo_dec = _geo_agent.decide({"country": "system", "roas": avg_roas})
        audience_dec = _audience_agent.decide({"ctr": avg_ctr, "cvr": avg_cvr})
        risk_input = {
            "current_capital": _state.capital,
            "peak_capital": _current_peak_capital(),
            "today_spend": _global_risk_engine.today_spend(),
            "roas": avg_roas,
            "kill_switch": _global_risk_engine.kill_switch_active,
        }
        risk_dec = _risk_agent.decide(risk_input)

        for dec in [scaling_dec, geo_dec, audience_dec, risk_dec]:
            _agent_metrics.record_decision(dec.agent, dec.action)

    return {
        "agents": _agent_metrics.snapshot(),
        "risk_status": _global_risk_engine.status(),
    }


@app.get("/risk/status")
def risk_engine_status():
    """Global risk engine status: kill-switch, daily spend, drawdown caps."""
    return _global_risk_engine.status()


@app.post("/risk/killswitch/activate")
def activate_kill_switch(reason: str = "manual"):
    """Activate the global kill-switch — halts all new spend immediately."""
    _global_risk_engine.activate_kill_switch(reason=reason)
    return {"kill_switch_active": True, "reason": reason}


@app.post("/risk/killswitch/deactivate")
def deactivate_kill_switch():
    """Deactivate the global kill-switch — resumes normal operation."""
    _global_risk_engine.deactivate_kill_switch()
    return {"kill_switch_active": False}


@app.get("/capital_allocation")
def capital_allocation():
    """Capital allocation view: portfolio split and risk-adjusted budgets."""
    top = decide(_state)[:5]
    budgets = budget_allocate(top)

    total = sum(budgets) or 1.0
    result = []
    for i, d in enumerate(top):
        raw_budget = budgets[i]
        # enforce through global risk engine
        override = _global_risk_engine.enforce(
            proposed_budget=raw_budget,
            current_capital=_state.capital,
            peak_capital=_current_peak_capital(),
        )
        safe_budget = override.adjusted_budget if override.allowed else 0.0
        result.append({
            "variant": d["action"].get("variant"),
            "raw_budget": round(raw_budget, 2),
            "safe_budget": round(safe_budget, 2),
            "allocation_pct": round(raw_budget / total * 100, 2),
            "risk_override": override.triggered_cap != "" or not override.allowed,
            "risk_reason": override.reason,
            "pred": round(d.get("pred", 0), 4),
        })

    return {
        "total_budget": round(total, 2),
        "risk_status": _global_risk_engine.status(),
        "allocations": result,
    }


@app.get("/prediction_errors")
def prediction_errors(limit: int = Query(default=100, ge=1, le=500)):
    """Prediction error chart: recent (predicted, actual, error) pairs with calibration stats."""
    errors = _wm_calibrator.prediction_errors()[-limit:]
    stats = _wm_calibrator.stats()
    return {
        "errors": errors,
        "calibration": stats,
        "total_updates": _wm_calibrator.total_updates,
    }
