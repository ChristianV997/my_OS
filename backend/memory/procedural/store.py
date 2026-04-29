"""ProceduralStore — reusable workflow recipes and execution policies.

Procedural memory holds distilled execution knowledge: workflows that worked,
policies that converged, hook-product pairings that generated high ROAS.

Unlike episodic memory (raw events) and semantic memory (compressed concepts),
procedural memory is action-oriented:
  - A Procedure is a named, reusable execution recipe
  - Procedures are extracted from successful WorkflowArtifacts
  - They carry pre-conditions, steps, and expected outcomes
  - They are scored and ranked by historical success rate

This is the memory tier that enables the system to 'learn to do' rather
than just 'remember what happened'.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any


class Procedure:
    """A reusable execution recipe extracted from successful workflow history."""
    __slots__ = ("procedure_id", "name", "domain", "steps", "preconditions",
                 "expected_outcomes", "success_count", "failure_count",
                 "avg_roas", "version", "ts", "metadata")

    def __init__(
        self,
        procedure_id:      str,
        name:              str,
        domain:            str,           # campaign | signal | simulation | creative
        steps:             list[dict[str, Any]],
        preconditions:     dict[str, Any] | None = None,
        expected_outcomes: dict[str, Any] | None = None,
        avg_roas:          float = 0.0,
        version:           int   = 1,
        metadata:          dict[str, Any] | None = None,
    ) -> None:
        self.procedure_id      = procedure_id
        self.name              = name
        self.domain            = domain
        self.steps             = steps
        self.preconditions     = preconditions or {}
        self.expected_outcomes = expected_outcomes or {}
        self.success_count     = 0
        self.failure_count     = 0
        self.avg_roas          = avg_roas
        self.version           = version
        self.ts                = time.time()
        self.metadata          = metadata or {}

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def record_outcome(self, success: bool, roas: float = 0.0) -> None:
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        if roas > 0:
            total = self.success_count + self.failure_count
            self.avg_roas = (self.avg_roas * (total - 1) + roas) / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "procedure_id":      self.procedure_id,
            "name":              self.name,
            "domain":            self.domain,
            "steps":             self.steps,
            "preconditions":     self.preconditions,
            "expected_outcomes": self.expected_outcomes,
            "success_count":     self.success_count,
            "failure_count":     self.failure_count,
            "success_rate":      self.success_rate,
            "avg_roas":          self.avg_roas,
            "version":           self.version,
            "ts":                self.ts,
            "metadata":          self.metadata,
        }


class ProceduralStore:
    """Thread-safe store of Procedure objects indexed by domain and name."""

    def __init__(self) -> None:
        self._lock:      threading.Lock             = threading.Lock()
        self._procs:     dict[str, Procedure]       = {}  # id → proc
        self._by_domain: dict[str, list[Procedure]] = {}

    def register(self, proc: Procedure) -> None:
        with self._lock:
            self._procs[proc.procedure_id] = proc
            self._by_domain.setdefault(proc.domain, []).append(proc)

    def create(
        self,
        name:   str,
        domain: str,
        steps:  list[dict[str, Any]],
        **kwargs: Any,
    ) -> Procedure:
        pid  = uuid.uuid4().hex[:12]
        proc = Procedure(procedure_id=pid, name=name, domain=domain,
                         steps=steps, **kwargs)
        self.register(proc)
        return proc

    def get(self, procedure_id: str) -> Procedure | None:
        with self._lock:
            return self._procs.get(procedure_id)

    def best_for_domain(self, domain: str, k: int = 5) -> list[Procedure]:
        """Return top-k procedures by success rate × avg_roas."""
        with self._lock:
            procs = list(self._by_domain.get(domain, []))
        return sorted(procs,
                      key=lambda p: p.success_rate * max(p.avg_roas, 1.0),
                      reverse=True)[:k]

    def record_outcome(
        self, procedure_id: str, success: bool, roas: float = 0.0
    ) -> None:
        with self._lock:
            proc = self._procs.get(procedure_id)
            if proc:
                proc.record_outcome(success, roas)

    def count(self, domain: str | None = None) -> int:
        with self._lock:
            if domain:
                return len(self._by_domain.get(domain, []))
            return len(self._procs)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._procs.values()]
