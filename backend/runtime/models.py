"""backend.runtime.models — typed domain models for the canonical runtime state.

These dataclasses are the single source of truth for every domain entity the
runtime produces.  All serialization (WebSocket, Redis, DuckDB) goes through
these types so there is never a schema mismatch between components.

Design rules
------------
- Every field has a default so instances can be created with zero args.
- ``to_dict()`` returns a plain dict (JSON-safe primitives only).
- ``from_dict()`` is provided for each type that arrives as an external dict.
- No business logic here — pure data containers.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any


# ── helpers ───────────────────────────────────────────────────────────────────

def _f(v: Any, default: float = 0.0) -> float:
    try: return float(v) if v is not None else default
    except (TypeError, ValueError): return default

def _i(v: Any, default: int = 0) -> int:
    try: return int(v) if v is not None else default
    except (TypeError, ValueError): return default

def _s(v: Any, default: str = "") -> str:
    return str(v) if v is not None else default


# ── leaf domain models ────────────────────────────────────────────────────────

@dataclass
class MetricsRecord:
    capital:      float = 0.0
    avg_roas:     float = 0.0
    win_rate:     float = 0.0
    cycle:        int   = 0
    phase:        str   = "RESEARCH"
    regime:       str   = "unknown"
    signal_count: int   = 0
    ts:           float = field(default_factory=time.time)

    def to_dict(self) -> dict: return asdict(self)


@dataclass
class SignalRecord:
    product:  str   = ""
    score:    float = 0.0
    source:   str   = ""
    velocity: float = 0.0
    platform: str   = ""
    ts:       float = field(default_factory=time.time)

    def to_dict(self) -> dict: return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SignalRecord":
        return cls(
            product=_s(d.get("product")),
            score=_f(d.get("score")),
            source=_s(d.get("source")),
            velocity=_f(d.get("velocity")),
            platform=_s(d.get("platform")),
            ts=_f(d.get("ts"), time.time()),
        )


@dataclass
class SimulationRecord:
    product:             str   = ""
    rank:                int   = 0
    predicted_roas:      float = 0.0
    corrected_roas:      float = 0.0
    predicted_ctr:       float = 0.0
    predicted_engagement:float = 0.0
    confidence:          float = 0.0
    risk_score:          float = 0.0
    rank_score:          float = 0.0
    hook:                str   = ""
    angle:               str   = ""
    ts:                  float = field(default_factory=time.time)

    def to_dict(self) -> dict: return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SimulationRecord":
        return cls(
            product=_s(d.get("product")),
            rank=_i(d.get("rank")),
            predicted_roas=_f(d.get("predicted_roas")),
            corrected_roas=_f(d.get("corrected_roas")),
            predicted_ctr=_f(d.get("predicted_ctr")),
            predicted_engagement=_f(d.get("predicted_engagement")),
            confidence=_f(d.get("confidence")),
            risk_score=_f(d.get("risk_score")),
            rank_score=_f(d.get("rank_score")),
            hook=_s(d.get("hook")),
            angle=_s(d.get("angle")),
            ts=_f(d.get("ts"), time.time()),
        )


@dataclass
class PlaybookRecord:
    product:        str       = ""
    phase:          str       = ""
    top_hooks:      list[str] = field(default_factory=list)
    top_angles:     list[str] = field(default_factory=list)
    estimated_roas: float     = 0.0
    confidence:     float     = 0.0
    evidence_count: int       = 0
    created_at:     float     = field(default_factory=time.time)

    def to_dict(self) -> dict: return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PlaybookRecord":
        return cls(
            product=_s(d.get("product")),
            phase=_s(d.get("phase")),
            top_hooks=list(d.get("top_hooks") or []),
            top_angles=list(d.get("top_angles") or []),
            estimated_roas=_f(d.get("estimated_roas")),
            confidence=_f(d.get("confidence")),
            evidence_count=_i(d.get("evidence_count")),
            created_at=_f(d.get("created_at"), time.time()),
        )


@dataclass
class WorkerRecord:
    name:        str         = ""
    status:      str         = "unknown"
    kind:        str         = "unknown"
    last_run_ts: float | None = None
    run_count:   int         = 0
    active:      bool        = False

    def to_dict(self) -> dict: return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WorkerRecord":
        return cls(
            name=_s(d.get("name")),
            status=_s(d.get("last_status", d.get("status", "unknown"))),
            kind=_s(d.get("kind", "unknown")),
            last_run_ts=d.get("last_run_ts"),
            run_count=_i(d.get("run_count")),
            active=bool(d.get("active", False)),
        )


@dataclass
class DecisionRecord:
    roas:       float = 0.0
    ctr:        float = 0.0
    cvr:        float = 0.0
    hook:       str   = ""
    angle:      str   = ""
    label:      str   = "NEUTRAL"
    product:    str   = ""
    env_regime: str   = ""
    ts:         float = field(default_factory=time.time)

    def to_dict(self) -> dict: return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionRecord":
        return cls(
            roas=_f(d.get("roas")),
            ctr=_f(d.get("ctr")),
            cvr=_f(d.get("cvr")),
            hook=_s(d.get("hook")),
            angle=_s(d.get("angle")),
            label=_s(d.get("label", "NEUTRAL")),
            product=_s(d.get("product")),
            env_regime=_s(d.get("env_regime")),
            ts=_f(d.get("ts"), time.time()),
        )


@dataclass
class AlertRecord:
    level:   str   = "info"   # info | warning | error | critical
    message: str   = ""
    source:  str   = ""
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict: return asdict(self)


@dataclass
class OrchestratorRecord:
    phase:         str         = "RESEARCH"
    tick:          int         = 0
    last_tick_ts:  float | None = None
    worker_count:  int         = 0
    is_running:    bool        = True

    def to_dict(self) -> dict: return asdict(self)
