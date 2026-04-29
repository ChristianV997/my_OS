"""backend.runtime.sleep — cognitive sleep runtime (Phase 4).

The sleep runtime closes the memory lifecycle: events accumulate during
waking operation, then periodic sleep cycles consolidate them into stable
long-term representations.

Architecture mirrors hippocampal replay / predictive processing:
  - ReplayBatch  → input snapshot (like hippocampal reactivation)
  - EpisodicCompaction → raw events → semantic units
  - SemanticCompression → deduplication / abstraction
  - ProceduralReinforcement → habit formation
  - MemoryDecay → controlled forgetting
  - LineageSummarization → causal compaction
  - SemanticCheckpoint → stable long-term state

Public entry points:
    ConsolidationEngine  — run one sleep cycle synchronously
    ReplayScheduler / get_scheduler()  — background daemon
    run_cycle_now()      — convenience one-liner

Schemas:    ConsolidationResult, ReplayBatch, SemanticCheckpoint, LineageSummary
Policies:   DecayPolicy, ReinforcementPolicy, RetentionPolicy, CompressionPolicy
Adapters:   VectorAdapter, LineageAdapter, MemoryAdapter, ReplayAdapter, TelemetryAdapter
"""
from .consolidation_engine import ConsolidationEngine
from .replay_scheduler     import ReplayScheduler, get_scheduler
from .schemas              import (
    ConsolidationResult, ReplayBatch, SemanticCheckpoint, LineageSummary,
)
from .policies             import (
    DecayPolicy, ReinforcementPolicy, RetentionPolicy, RetentionDecision,
    CompressionPolicy,
)
from .adapters             import (
    VectorAdapter, LineageAdapter, MemoryAdapter, ReplayAdapter, TelemetryAdapter,
)


def run_cycle_now(workspace: str = "default", window_hours: float = 24.0) -> ConsolidationResult:
    """Trigger one consolidation cycle synchronously and return the result."""
    engine = ConsolidationEngine(workspace=workspace, window_hours=window_hours)
    return engine.run_cycle()


__all__ = [
    "ConsolidationEngine",
    "ReplayScheduler", "get_scheduler",
    "run_cycle_now",
    "ConsolidationResult", "ReplayBatch", "SemanticCheckpoint", "LineageSummary",
    "DecayPolicy", "ReinforcementPolicy", "RetentionPolicy", "RetentionDecision",
    "CompressionPolicy",
    "VectorAdapter", "LineageAdapter", "MemoryAdapter", "ReplayAdapter", "TelemetryAdapter",
]
