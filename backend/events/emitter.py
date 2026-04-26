"""backend.events.emitter — typed event emission helpers.

All runtime components (orchestrator, API background runner, workers) call
these functions instead of calling ``core.stream.publish()`` directly.

Why
---
- Single call site ensures every event goes through the broker (replay buffer,
  EventEnvelope wrapping, structured logging).
- Type annotations make call sites readable and catch schema drift early.
- Falls back silently so a broker import error never crashes a worker.

Usage
-----
    from backend.events.emitter import emit_tick, emit_snapshot, emit_worker_health

    emit_tick("EXPLORE", avg_roas=1.4, capital=820.0, win_rate=0.6)
    emit_snapshot(snap)
    emit_worker_health("feedback_collection_worker", "ok", phase="EXPLORE")
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


def _broker():
    from backend.pubsub.broker import broker as _b
    return _b


def emit_snapshot(snap: Any, source: str = "api") -> None:
    """Emit a full RuntimeSnapshot to the event bus."""
    try:
        _broker().emit_snapshot(snap)
    except Exception as exc:
        _log.warning("emit_snapshot_failed error=%s", exc)


def emit_tick(
    phase: str,
    avg_roas: float,
    capital: float,
    win_rate: float = 0.0,
    signal_count: int = 0,
    source: str = "orchestrator",
) -> None:
    """Emit a lightweight orchestrator tick event."""
    try:
        _broker().emit_tick(
            phase=phase,
            avg_roas=avg_roas,
            capital=capital,
            win_rate=win_rate,
            signal_count=signal_count,
            source=source,
        )
    except Exception as exc:
        _log.warning("emit_tick_failed error=%s", exc)


def emit_worker_health(
    worker: str,
    status: str,
    phase: str = "",
    source: str = "orchestrator",
    **extra: Any,
) -> None:
    """Emit a worker health / completion event."""
    try:
        _broker().emit_worker_health(
            worker=worker,
            status=status,
            phase=phase,
            source=source,
            **extra,
        )
    except Exception as exc:
        _log.warning("emit_worker_health_failed worker=%s error=%s", worker, exc)


def emit_task_inventory(inv: dict) -> None:
    """Emit a task inventory snapshot."""
    try:
        _broker().emit_task_inventory(inv)
    except Exception as exc:
        _log.warning("emit_task_inventory_failed error=%s", exc)


def emit_signals_updated(signals: list[dict], source: str = "api") -> None:
    """Emit a signals.updated event when fresh signals are available."""
    try:
        _broker().emit_signals_updated(signals, source=source)
    except Exception as exc:
        _log.warning("emit_signals_updated_failed error=%s", exc)


def emit_simulation_completed(
    scores: list[dict],
    top_product: str | None = None,
    source: str = "simulation",
) -> None:
    """Emit simulation.completed after score_signals() finishes."""
    try:
        _broker().emit_simulation_completed(scores, top_product=top_product, source=source)
    except Exception as exc:
        _log.warning("emit_simulation_completed_failed error=%s", exc)


def emit_anomaly(level: str, message: str, source: str = "system") -> None:
    """Emit an anomaly.detected event (worker crash, budget overrun, etc.)."""
    try:
        _broker().emit_anomaly(level=level, message=message, source=source)
    except Exception as exc:
        _log.warning("emit_anomaly_failed error=%s", exc)


def emit_decision(
    product: str,
    roas: float,
    label: str,
    hook: str = "",
    angle: str = "",
    source: str = "api",
    **extra: Any,
) -> None:
    """Emit a decision.logged event for a classified outcome."""
    try:
        _broker().emit_decision(
            product=product, roas=roas, label=label,
            hook=hook, angle=angle, source=source, **extra,
        )
    except Exception as exc:
        _log.warning("emit_decision_failed error=%s", exc)


def emit_metrics_ingested(
    source: str,
    metrics: dict[str, Any],
) -> None:
    """Emit a metrics.ingested event for engagement/retention/campaign data.

    ``metrics`` is a free-form dict; common keys include engagement_rate,
    retention_rate, ctr, cvr, spend, revenue, roas, views, likes, shares.
    All metric values are routed through the standard event bus so they
    appear in the replay log and can be consumed by any subscriber.
    """
    try:
        _broker().emit_metrics_ingested(source=source, metrics=metrics)
    except Exception as exc:
        _log.warning("emit_metrics_ingested_failed source=%s error=%s", source, exc)


def emit_heartbeat(source: str = "system") -> None:
    """Emit a periodic runtime liveness signal.

    Distinct from the WebSocket heartbeat frame — this is a broker event
    that appears in the durable replay log, confirming the runtime is alive.
    """
    try:
        _broker().emit_heartbeat(source=source)
    except Exception as exc:
        _log.warning("emit_heartbeat_failed error=%s", exc)


def emit_runtime_consistency(
    issues: list[str],
    source: str = "runtime",
) -> None:
    """Emit a runtime.consistency event when validation detects drift.

    ``issues`` is a list of human-readable problem descriptions.  An empty
    list means the consistency check passed (still emitted as a confirmation).
    """
    try:
        _broker().emit_runtime_consistency(issues=issues, source=source)
    except Exception as exc:
        _log.warning("emit_runtime_consistency_failed error=%s", exc)
