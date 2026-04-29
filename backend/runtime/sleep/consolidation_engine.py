"""ConsolidationEngine — orchestrates a single cognitive sleep cycle.

One cycle:
  1. Extract replay window (ReplayBatch)
  2. Episodic compaction → SemanticStore units
  3. Semantic compression → deduplicate/merge units
  4. Procedural reinforcement → update ProceduralStore
  5. Memory decay → prune low-retention memories
  6. Lineage summarization → checkpoint + compact deep branches
  7. SemanticCheckpoint → snapshot for next cycle
  8. Emit ConsolidationResult to event log

All steps are isolated; a failure in one does not abort the cycle.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from .schemas.consolidation_result import ConsolidationResult
from .schemas.semantic_checkpoint  import SemanticCheckpoint
from .policies.compression_policy  import CompressionPolicy
from .policies.decay_policy        import DecayPolicy
from .policies.retention_policy    import RetentionPolicy
from .policies.reinforcement_policy import ReinforcementPolicy
from .replay_window               import extract_window
from .episodic_compaction         import compact
from .semantic_compression        import compress_all
from .memory_decay                import run_decay_pass
from .procedural_reinforcement    import reinforce_from_batch
from .lineage_summarization       import summarize_deep_branches, checkpoint_lineage

log = logging.getLogger(__name__)


class ConsolidationEngine:
    """Executes deterministic cognitive sleep cycles.

    Instantiate with optional policy overrides; call ``run_cycle()`` to
    execute one full pass.  All operations are workspace-bounded.
    """

    def __init__(
        self,
        workspace:            str = "default",
        window_hours:         float = 24.0,
        compression_policy:   CompressionPolicy   | None = None,
        decay_policy:         DecayPolicy          | None = None,
        retention_policy:     RetentionPolicy      | None = None,
        reinforcement_policy: ReinforcementPolicy  | None = None,
        index_vectors:        bool = True,
    ) -> None:
        self.workspace            = workspace
        self.window_hours         = window_hours
        self.compression_policy   = compression_policy   or CompressionPolicy()
        self.decay_policy         = decay_policy          or DecayPolicy()
        self.retention_policy     = retention_policy      or RetentionPolicy()
        self.reinforcement_policy = reinforcement_policy  or ReinforcementPolicy()
        self.index_vectors        = index_vectors
        self._last_checkpoint_id  = ""

    def run_cycle(self) -> ConsolidationResult:
        """Execute one full sleep cycle. Returns ConsolidationResult."""
        cycle_id = uuid.uuid4().hex[:12]
        result   = ConsolidationResult(
            cycle_id=cycle_id,
            workspace=self.workspace,
        )
        log.info("ConsolidationEngine: starting cycle %s (workspace=%s)", cycle_id, self.workspace)

        # Step 1: Extract replay window
        try:
            batch = extract_window(
                window_hours=self.window_hours,
                workspace=self.workspace,
            )
            result.episodes_read = batch.size
            log.debug("cycle %s: extracted %d events", cycle_id, batch.size)
        except Exception as exc:
            result.errors.append(f"replay_window: {exc}")
            result.finish()
            return result

        # Step 2: Episodic compaction → SemanticStore
        try:
            compacted = compact(batch, self.compression_policy, self.index_vectors)
            result.episodes_compacted     = batch.size
            result.semantic_units_created = sum(compacted.values())
            log.debug("cycle %s: compacted → %d semantic units", cycle_id, result.semantic_units_created)
        except Exception as exc:
            result.errors.append(f"episodic_compaction: {exc}")

        # Step 3: Semantic compression (dedup/merge)
        try:
            merged = compress_all(self.compression_policy)
            result.semantic_units_pruned = sum(p for _, p in merged.values())
            log.debug("cycle %s: compressed %d semantic units", cycle_id, result.semantic_units_pruned)
        except Exception as exc:
            result.errors.append(f"semantic_compression: {exc}")

        # Step 4: Procedural reinforcement
        try:
            reinforced = reinforce_from_batch(batch, self.reinforcement_policy)
            result.procedures_reinforced = reinforced
            log.debug("cycle %s: reinforced %d procedures", cycle_id, reinforced)
        except Exception as exc:
            result.errors.append(f"procedural_reinforcement: {exc}")

        # Step 5: Memory decay
        try:
            decay_result = run_decay_pass(self.decay_policy, self.retention_policy)
            result.decay_applied      = True
            result.procedures_deprecated = decay_result.get("procedures_deprecated", 0)
            log.debug("cycle %s: decay applied, deprecated=%d", cycle_id, result.procedures_deprecated)
        except Exception as exc:
            result.errors.append(f"memory_decay: {exc}")

        # Step 6: Lineage summarization
        try:
            summaries = summarize_deep_branches(
                workspace=self.workspace,
                cycle_id=cycle_id,
                policy=self.compression_policy,
            )
            result.lineage_nodes_summarized = sum(s.collapsed_count for s in summaries)
            checkpoint_lineage(workspace=self.workspace, cycle_id=cycle_id)
            log.debug("cycle %s: summarized %d lineage nodes", cycle_id, result.lineage_nodes_summarized)
        except Exception as exc:
            result.errors.append(f"lineage_summarization: {exc}")

        # Step 7: Semantic checkpoint
        try:
            ckpt = SemanticCheckpoint.from_semantic_store(
                checkpoint_id=uuid.uuid4().hex[:12],
                cycle_id=cycle_id,
                workspace=self.workspace,
                parent_checkpoint_id=self._last_checkpoint_id,
            )
            self._last_checkpoint_id = ckpt.checkpoint_id
            _emit_checkpoint(ckpt)
        except Exception as exc:
            result.errors.append(f"semantic_checkpoint: {exc}")

        # Step 8: Finalize and emit
        result.finish()
        _emit_result(result)
        log.info(
            "ConsolidationEngine: cycle %s done in %.2fs — "
            "compacted=%d semantic=%d reinforced=%d errors=%d",
            cycle_id, result.duration_s,
            result.episodes_compacted,
            result.semantic_units_created,
            result.procedures_reinforced,
            len(result.errors),
        )
        return result


# ── telemetry helpers ─────────────────────────────────────────────────────────

def _emit_result(result: ConsolidationResult) -> None:
    try:
        from backend.events.log import append
        append(
            "sleep.consolidation.completed",
            payload=result.to_dict(),
            source="consolidation_engine",
        )
    except Exception:
        pass


def _emit_checkpoint(ckpt: SemanticCheckpoint) -> None:
    try:
        from backend.events.log import append
        append(
            "sleep.semantic.checkpoint",
            payload=ckpt.to_dict(),
            source="consolidation_engine",
        )
    except Exception:
        pass
