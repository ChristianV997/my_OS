"""Tests for runtime consolidation: event schemas, simulation-in-snapshot,
race-condition guard, and canonical event flow."""
import time


# ── event schemas ─────────────────────────────────────────────────────────────

def test_event_schema_constants_importable():
    from backend.events.schemas import (
        ORCHESTRATOR_TICK, SIGNALS_UPDATED, SIMULATION_COMPLETED,
        PLAYBOOK_UPDATED, CAMPAIGN_UPDATED, ANOMALY_DETECTED,
        WORKER_HEALTH, RUNTIME_SNAPSHOT, TASK_INVENTORY, DECISION_LOGGED,
    )
    assert all(isinstance(v, str) for v in [
        ORCHESTRATOR_TICK, SIGNALS_UPDATED, SIMULATION_COMPLETED,
        PLAYBOOK_UPDATED, CAMPAIGN_UPDATED, ANOMALY_DETECTED,
        WORKER_HEALTH, RUNTIME_SNAPSHOT, TASK_INVENTORY, DECISION_LOGGED,
    ])


def test_event_schemas_package_re_exports():
    import backend.events as ev
    assert hasattr(ev, "ORCHESTRATOR_TICK")
    assert hasattr(ev, "RUNTIME_SNAPSHOT")
    assert hasattr(ev, "TASK_INVENTORY")


def test_legacy_aliases_present():
    from backend.events.schemas import LEGACY_TICK, LEGACY_WORKER, LEGACY_SNAPSHOT
    assert LEGACY_TICK == "tick"
    assert LEGACY_WORKER == "worker"
    assert LEGACY_SNAPSHOT == "snapshot"


def test_no_duplicate_type_values():
    """Each canonical type must be unique (no two constants share the same string)."""
    from backend.events import schemas
    canonical = [
        schemas.ORCHESTRATOR_TICK, schemas.SIGNALS_UPDATED,
        schemas.SIMULATION_COMPLETED, schemas.PLAYBOOK_UPDATED,
        schemas.CAMPAIGN_UPDATED, schemas.ANOMALY_DETECTED,
        schemas.WORKER_HEALTH, schemas.RUNTIME_SNAPSHOT,
        schemas.TASK_INVENTORY, schemas.DECISION_LOGGED,
    ]
    assert len(canonical) == len(set(canonical)), "Duplicate event type strings found"


# ── RuntimeSnapshot with simulation_scores ────────────────────────────────────

def test_runtime_snapshot_has_simulation_scores_field():
    from backend.runtime.state import RuntimeSnapshot
    snap = RuntimeSnapshot()
    assert hasattr(snap, "simulation_scores")
    assert isinstance(snap.simulation_scores, list)


def test_runtime_snapshot_to_dict_includes_simulation_scores():
    from backend.runtime.state import RuntimeSnapshot
    snap = RuntimeSnapshot(simulation_scores=[{"rank": 1, "product": "shoes"}])
    d = snap.to_dict()
    assert "simulation_scores" in d
    assert d["simulation_scores"][0]["product"] == "shoes"


def test_build_snapshot_returns_runtime_snapshot():
    from backend.runtime.state import build_snapshot, RuntimeSnapshot
    from backend.core.state import SystemState
    state = SystemState()
    snap = build_snapshot(state)
    assert isinstance(snap, RuntimeSnapshot)
    assert hasattr(snap, "simulation_scores")
    assert isinstance(snap.simulation_scores, list)


def test_build_snapshot_simulation_scores_are_dicts():
    from backend.runtime.state import build_snapshot
    from backend.core.state import SystemState
    state = SystemState()
    snap = build_snapshot(state)
    for score in snap.simulation_scores:
        assert isinstance(score, dict)
        assert "rank" in score or "product" in score


# ── race condition guard ──────────────────────────────────────────────────────

def test_orchestrator_handles_cycles_env_var_reads():
    """Verify the env var guard module-level constant is a bool."""
    import importlib, os
    # just check the attribute exists in api module namespace
    # (we can't easily test the actual guard without starting threads)
    import backend.api as api_mod
    assert hasattr(api_mod, "_ORCHESTRATOR_HANDLES_CYCLES")
    assert isinstance(api_mod._ORCHESTRATOR_HANDLES_CYCLES, bool)


def test_orchestrator_handles_cycles_default_false():
    import backend.api as api_mod
    # Default must be False so existing single-process deploys keep working
    import os
    if os.getenv("ORCHESTRATOR_HANDLES_CYCLES", "").lower() not in ("true", "1"):
        assert api_mod._ORCHESTRATOR_HANDLES_CYCLES is False


# ── simulation scores flow into stream ────────────────────────────────────────

def test_simulation_scores_publish_in_snapshot_dict():
    from backend.runtime.state import RuntimeSnapshot
    scores = [
        {"rank": 1, "product": "shoes", "predicted_engagement": 0.8,
         "predicted_roas": 2.1, "corrected_roas": 1.9, "confidence": 0.6,
         "risk_score": 0.3, "rank_score": 0.65, "ts": time.time(),
         "hook": "urgency", "angle": "price", "predicted_ctr": 0.03},
    ]
    snap = RuntimeSnapshot(simulation_scores=scores)
    d = snap.to_dict()
    assert d["simulation_scores"][0]["predicted_roas"] == 2.1
    assert d["simulation_scores"][0]["corrected_roas"] == 1.9


# ── event schema constants match known strings ────────────────────────────────

def test_task_inventory_type_matches_existing_publisher():
    """task_inventory type string must match what task_registry.to_stream() produces."""
    from backend.events.schemas import TASK_INVENTORY
    from backend.runtime.task_inventory import task_registry
    snap = task_registry.to_stream()
    assert snap["type"] == TASK_INVENTORY


def test_snapshot_legacy_type_matches_runtime_snapshot():
    """RuntimeSnapshot.type must match the LEGACY_SNAPSHOT constant."""
    from backend.events.schemas import LEGACY_SNAPSHOT
    from backend.runtime.state import RuntimeSnapshot
    snap = RuntimeSnapshot()
    assert snap.type == LEGACY_SNAPSHOT


# ── simulation engine integrates with snapshot pipeline ──────────────────────

def test_simulation_engine_score_signals_called_with_snapshot_signals():
    from simulation.engine import SimulationEngine
    engine = SimulationEngine()
    signals = [
        {"product": "shoes", "score": 0.9, "source": "trends"},
        {"product": "hat",   "score": 0.5, "source": "trends"},
    ]
    results = engine.score_signals(signals)
    assert len(results) == 2
    assert results[0].rank == 1
    assert all(hasattr(r, "to_dict") for r in results)
    dicts = [r.to_dict() for r in results]
    assert all("predicted_roas" in d for d in dicts)
    assert all("corrected_roas" in d for d in dicts)
