"""Tests for backend.runtime.models typed domain models."""
import time


def test_metrics_record_defaults():
    from backend.runtime.models import MetricsRecord
    m = MetricsRecord()
    assert m.capital == 0.0
    assert m.phase == "RESEARCH"
    assert m.regime == "unknown"
    assert isinstance(m.ts, float)


def test_metrics_record_to_dict_round_trips():
    from backend.runtime.models import MetricsRecord
    m = MetricsRecord(capital=500.0, avg_roas=1.4, cycle=7, phase="EXPLORE")
    d = m.to_dict()
    assert d["capital"] == 500.0
    assert d["avg_roas"] == 1.4
    assert d["phase"] == "EXPLORE"


def test_signal_record_from_dict():
    from backend.runtime.models import SignalRecord
    d = {"product": "shoes", "score": 0.9, "source": "trends", "velocity": 0.3}
    s = SignalRecord.from_dict(d)
    assert s.product == "shoes"
    assert s.score == 0.9
    assert s.velocity == 0.3


def test_signal_record_handles_missing_fields():
    from backend.runtime.models import SignalRecord
    s = SignalRecord.from_dict({})
    assert s.product == ""
    assert s.score == 0.0


def test_simulation_record_from_dict():
    from backend.runtime.models import SimulationRecord
    d = {
        "product": "hat", "rank": 2,
        "predicted_roas": 1.8, "corrected_roas": 1.7,
        "confidence": 0.5, "risk_score": 0.3, "rank_score": 0.6,
        "hook": "urgency", "angle": "price",
    }
    r = SimulationRecord.from_dict(d)
    assert r.product == "hat"
    assert r.rank == 2
    assert r.corrected_roas == 1.7
    assert r.hook == "urgency"


def test_playbook_record_from_dict():
    from backend.runtime.models import PlaybookRecord
    d = {
        "product": "shoes", "phase": "EXPLORE",
        "top_hooks": ["urgency", "social_proof"],
        "top_angles": ["price", "quality"],
        "estimated_roas": 2.1, "confidence": 0.6, "evidence_count": 15,
    }
    p = PlaybookRecord.from_dict(d)
    assert p.product == "shoes"
    assert "urgency" in p.top_hooks
    assert p.confidence == 0.6


def test_worker_record_from_dict():
    from backend.runtime.models import WorkerRecord
    now = time.time()
    d = {"name": "bg_runner", "last_status": "ok", "kind": "thread",
         "last_run_ts": now, "run_count": 42, "active": True}
    w = WorkerRecord.from_dict(d)
    assert w.name == "bg_runner"
    assert w.status == "ok"
    assert w.run_count == 42
    assert w.active is True


def test_decision_record_from_dict():
    from backend.runtime.models import DecisionRecord
    d = {"roas": 2.0, "ctr": 0.03, "cvr": 0.02,
         "hook": "urgency", "angle": "price", "label": "WINNER", "product": "shoes"}
    dec = DecisionRecord.from_dict(d)
    assert dec.roas == 2.0
    assert dec.label == "WINNER"


def test_alert_record_to_dict():
    from backend.runtime.models import AlertRecord
    a = AlertRecord(level="error", message="overspend", source="risk_engine")
    d = a.to_dict()
    assert d["level"] == "error"
    assert d["message"] == "overspend"
    assert "ts" in d


def test_orchestrator_record_defaults():
    from backend.runtime.models import OrchestratorRecord
    o = OrchestratorRecord()
    assert o.phase == "RESEARCH"
    assert o.is_running is True
    assert o.tick == 0


def test_all_records_have_to_dict():
    from backend.runtime.models import (
        MetricsRecord, SignalRecord, SimulationRecord, PlaybookRecord,
        WorkerRecord, DecisionRecord, AlertRecord, OrchestratorRecord,
    )
    for cls in [MetricsRecord, SignalRecord, SimulationRecord, PlaybookRecord,
                WorkerRecord, DecisionRecord, AlertRecord, OrchestratorRecord]:
        inst = cls()
        d = inst.to_dict()
        assert isinstance(d, dict)
