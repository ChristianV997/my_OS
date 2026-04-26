"""orchestrator.main — unified runtime spine.

This is the single entry-point that drives the entire OS loop:

  PhaseController
    → ResourceAllocator   (budget/worker fractions per phase)
    → SignalWorker         (ingest trends → core/signals)
    → ExecutionWorker      (run backend decision/execute/learn cycle)
    → FeedbackWorker       (content metrics → playbook memory)
    → ScalingWorker        (AJO scale/kill based on validated winners)

Each worker runs as a Celery task (or synchronously via the fallback when
Redis is unavailable). The orchestrator ticks every N seconds, picks the
active phase, and dispatches work proportional to the resource allocation.

Run standalone:
  python -m orchestrator.main

Or inside Docker Compose:
  docker compose up orchestrator
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

try:
    import structlog
    _log = structlog.get_logger(__name__)
except ImportError:
    import logging as _logging_fallback
    _log = _logging_fallback.getLogger(__name__)  # type: ignore[assignment]

from core.system.phase_controller import Phase, phase_controller
from core.system.resource_allocator import resource_allocator
from core.signals import signal_engine

TICK_INTERVAL   = float(os.getenv("ORCHESTRATOR_TICK_S", "10"))
TOTAL_BUDGET    = float(os.getenv("ORCHESTRATOR_BUDGET", "500"))
TOTAL_WORKERS   = int(os.getenv("ORCHESTRATOR_WORKERS", "4"))


# ── worker dispatchers ────────────────────────────────────────────────────────

def _run_signal_ingestion() -> dict[str, Any]:
    """Pull fresh signals and feed them to the intelligence loop."""
    try:
        signals = signal_engine.get()
        for _ in signals:
            phase_controller.record_signal()
        # Feed top keywords to core/intelligence_loop if available
        try:
            from core.intelligence_loop import run_intelligence
            keywords = [s.get("product", "") for s in signals if s.get("product")][:20]
            if keywords:
                run_intelligence(keywords)
        except Exception:
            pass
        return {"status": "ok", "signals": len(signals)}
    except Exception as exc:
        _log.exception("signal_ingestion_failed error=%s", exc)
        return {"status": "error", "error": str(exc)}


def _run_execution_cycle() -> dict[str, Any]:
    """Run one backend decision→execute→learn cycle."""
    try:
        from backend.execution.loop import run_cycle
        from backend.core.state import SystemState
        # Import shared state from api if running together; else use fresh state
        try:
            from backend.api import _state  # type: ignore[attr-defined]
            state = _state
        except Exception:
            state = SystemState()
        updated = run_cycle(state)
        return {
            "status":  "ok",
            "cycles":  updated.total_cycles,
            "capital": round(updated.capital, 2),
            "regime":  updated.detected_regime,
        }
    except Exception as exc:
        _log.exception("execution_cycle_failed error=%s", exc)
        return {"status": "error", "error": str(exc)}


def _run_feedback_collection() -> dict[str, Any]:
    """Classify recent content events, extract patterns, and update playbooks."""
    try:
        from core.content.feedback import batch_classify
        from core.content.patterns import extract_patterns, pattern_store
        from core.content.playbook import generate_playbook, playbook_memory
        try:
            from backend.api import _state  # type: ignore[attr-defined]
            rows = list(_state.event_log.rows[-50:])
        except Exception:
            rows = []
        if not rows:
            return {"status": "skipped", "reason": "no_events"}
        classified = batch_classify(rows)
        winners = [e for e in classified if e.get("label") == "WINNER"]
        if winners:
            patterns = extract_patterns(winners)
            pattern_store.update(patterns)
            products = {e.get("product", "") for e in winners if e.get("product")}
            for product in products:
                product_events = [e for e in classified if e.get("product") == product]
                try:
                    from core.system.phase_controller import phase_controller
                    phase = phase_controller.current.value
                except Exception:
                    phase = "EXPLORE"
                playbook_memory.upsert(generate_playbook(product, product_events, phase))
        return {"status": "ok", "classified": len(classified), "winners": len(winners)}
    except Exception as exc:
        _log.exception("feedback_collection_failed error=%s", exc)
        return {"status": "error", "error": str(exc)}


def _run_scaling() -> dict[str, Any]:
    """Scale/kill campaigns via AJO based on validated ROAS."""
    try:
        from backend.decision.portfolio_engine import top_products
        from backend.integrations.adobe_ajo import scale_campaign, is_configured
        if not is_configured():
            return {"status": "skipped", "reason": "AJO not configured"}
        winners = top_products(n=3)
        scaled = 0
        for p in winners:
            if p.get("weight", 0) > 0.3:
                scale_campaign(str(p.get("product_id", "")))
                scaled += 1
        return {"status": "ok", "scaled": scaled}
    except Exception as exc:
        _log.exception("scaling_failed error=%s", exc)
        return {"status": "error", "error": str(exc)}


def _run_simulation() -> dict[str, Any]:
    """Score and rank signal candidates before execution (simulation layer)."""
    try:
        from simulation.integration import _run_simulation as _sim
        result = _sim()
        return result
    except Exception as exc:
        _log.exception("simulation_worker_failed error=%s", exc)
        return {"status": "error", "error": str(exc)}


# ── worker retry + anomaly ────────────────────────────────────────────────────

# Track consecutive error counts per worker to gate anomaly emission
_worker_error_counts: dict[str, int] = {}
_ANOMALY_THRESHOLD = 2   # emit anomaly after this many consecutive errors


def _with_retry(fn: Any, attempts: int = 2) -> dict[str, Any]:
    """Run worker fn up to ``attempts`` times.

    - Returns first ``ok`` or ``skipped`` result immediately.
    - On repeated ``error`` status, emits an ``anomaly.detected`` event.
    - Never raises — always returns a status dict.
    """
    last_result: dict[str, Any] = {"status": "error", "error": "no_attempts"}
    for attempt in range(attempts):
        try:
            last_result = fn()
        except Exception as exc:
            last_result = {"status": "error", "error": str(exc)}
        if last_result.get("status") in ("ok", "skipped"):
            _worker_error_counts[fn.__name__] = 0
            return last_result
        # error path — wait a beat before retry (only if there are more attempts)
        if attempt < attempts - 1:
            time.sleep(0.5)

    # all attempts failed
    count = _worker_error_counts.get(fn.__name__, 0) + 1
    _worker_error_counts[fn.__name__] = count
    if count >= _ANOMALY_THRESHOLD:
        try:
            from backend.events.emitter import emit_anomaly
            emit_anomaly(
                level="error",
                message=f"worker_repeated_failure fn={fn.__name__} "
                        f"consecutive={count} error={last_result.get('error', '')}",
                source="orchestrator",
            )
        except Exception:
            pass
    return last_result


# ── phase dispatch table ───────────────────────────────────────────────────────

_PHASE_WORKERS: dict[Phase, list[Any]] = {
    Phase.RESEARCH:  [_run_simulation, _run_signal_ingestion, _run_signal_ingestion, _run_execution_cycle],
    Phase.EXPLORE:   [_run_simulation, _run_signal_ingestion, _run_execution_cycle, _run_execution_cycle, _run_feedback_collection],
    Phase.VALIDATE:  [_run_signal_ingestion, _run_execution_cycle, _run_feedback_collection, _run_feedback_collection],
    Phase.SCALE:     [_run_execution_cycle, _run_feedback_collection, _run_scaling, _run_scaling],
}


# ── metrics collection ────────────────────────────────────────────────────────

def _collect_metrics() -> dict[str, Any]:
    """Read KPIs needed by PhaseController.tick()."""
    try:
        from backend.api import _state  # type: ignore[attr-defined]
        rows = _state.event_log.rows
        recent = rows[-20:] if rows else []
        avg_roas = sum(r.get("roas", 0) for r in recent) / max(len(recent), 1)
        winners  = sum(1 for r in recent if r.get("roas", 0) >= 1.5)
        win_rate = winners / max(len(recent), 1)
        return {
            "avg_roas":     round(avg_roas, 4),
            "win_rate":     round(win_rate, 4),
            "capital":      round(_state.capital, 2),
            "signal_count": phase_controller.status()["signal_count"],
        }
    except Exception:
        return {"avg_roas": 0.0, "win_rate": 0.0, "capital": 0.0, "signal_count": 0}


# ── Prometheus instrumentation ────────────────────────────────────────────────

try:
    from prometheus_client import Counter, Gauge, start_http_server

    _phase_gauge    = Gauge("orchestrator_phase", "Current lifecycle phase", ["phase"])
    _cycle_counter  = Counter("orchestrator_cycles_total", "Total orchestrator ticks")
    _worker_counter = Counter("orchestrator_worker_runs_total", "Worker dispatch count", ["worker"])
    _PROMETHEUS_PORT = int(os.getenv("ORCHESTRATOR_METRICS_PORT", "9200"))

    def _init_prometheus() -> None:
        try:
            start_http_server(_PROMETHEUS_PORT)
            _log.info("prometheus_started port=%s", _PROMETHEUS_PORT)
        except Exception as exc:
            _log.warning("prometheus_start_failed error=%s", exc)

    def _record_phase(phase: Phase) -> None:
        for p in Phase:
            _phase_gauge.labels(phase=p.value).set(1 if p == phase else 0)

    def _record_worker(name: str) -> None:
        _worker_counter.labels(worker=name).inc()

    def _record_tick() -> None:
        _cycle_counter.inc()

except ImportError:
    def _init_prometheus() -> None: pass
    def _record_phase(_: Phase) -> None: pass
    def _record_worker(_: str) -> None: pass
    def _record_tick() -> None: pass


# ── main loop ─────────────────────────────────────────────────────────────────

def run() -> None:
    """Run the orchestrator loop indefinitely."""
    _log.info("orchestrator_starting tick_interval=%s", TICK_INTERVAL)
    _init_prometheus()

    while True:
        try:
            metrics = _collect_metrics()
            phase   = phase_controller.tick(metrics)
            alloc   = resource_allocator.describe(phase, TOTAL_BUDGET)

            _record_phase(phase)
            _record_tick()

            _log.info(
                "orchestrator_tick phase=%s avg_roas=%s capital=%s",
                phase.value,
                metrics.get("avg_roas"),
                metrics.get("capital"),
            )
            try:
                from backend.events.emitter import emit_tick as _emit_tick
                _emit_tick(
                    phase=phase.value,
                    avg_roas=metrics.get("avg_roas", 0.0),
                    capital=metrics.get("capital", 0.0),
                    win_rate=metrics.get("win_rate", 0.0),
                    signal_count=metrics.get("signal_count", 0),
                )
            except Exception:
                pass
            try:
                from backend.runtime.task_inventory import task_registry as _tr
                _tr.heartbeat("orchestrator_tick", status="ok")
            except Exception:
                pass

            for worker_fn in _PHASE_WORKERS.get(phase, []):
                result = _with_retry(worker_fn)
                _record_worker(worker_fn.__name__)
                if result.get("status") not in ("ok", "skipped"):
                    _log.warning("worker_error worker=%s result=%s", worker_fn.__name__, result)
                # Publish worker event via canonical emitter
                try:
                    from backend.events.emitter import emit_worker_health as _emit_wh
                    extra = {k: v for k, v in result.items()
                             if k not in ("status", "error") and isinstance(v, (int, float, str))}
                    _emit_wh(
                        worker=worker_fn.__name__,
                        status=result.get("status", "ok"),
                        phase=phase.value,
                        **extra,
                    )
                except Exception:
                    pass
                # Heartbeat task inventory
                _worker_task = {
                    "_run_signal_ingestion":   "signal_ingestion_worker",
                    "_run_execution_cycle":    "execution_cycle_worker",
                    "_run_feedback_collection": "feedback_collection_worker",
                    "_run_scaling":            "scaling_worker",
                    "_run_simulation":         "simulation_worker",
                }.get(worker_fn.__name__, worker_fn.__name__)
                try:
                    from backend.runtime.task_inventory import task_registry as _tr
                    _tr.heartbeat(_worker_task, status=result.get("status", "ok"))
                except Exception:
                    pass

        except (KeyboardInterrupt, SystemExit):
            _log.info("orchestrator_stopping")
            break
        except Exception as exc:
            _log.exception("orchestrator_tick_error error=%s", exc)

        time.sleep(TICK_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        import structlog as _sl
        _sl.configure(
            processors=[
                _sl.processors.TimeStamper(fmt="iso"),
                _sl.stdlib.add_log_level,
                _sl.processors.JSONRenderer(),
            ],
            wrapper_class=_sl.stdlib.BoundLogger,
            logger_factory=_sl.stdlib.LoggerFactory(),
        )
    except ImportError:
        pass
    run()
