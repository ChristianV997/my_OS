"""RetentionPolicy — what to keep, what to compact, what to discard.

Three-tier retention:
  KEEP      — retain as-is (high score, recent, high-ROAS)
  COMPACT   — merge into semantic unit (medium score, older)
  DISCARD   — prune entirely (low score, stale, redundant)
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import Enum


class RetentionDecision(Enum):
    KEEP    = "keep"
    COMPACT = "compact"
    DISCARD = "discard"


_KEEP_THRESHOLD    = float(os.getenv("SLEEP_RETAIN_KEEP",    "0.6"))
_COMPACT_THRESHOLD = float(os.getenv("SLEEP_RETAIN_COMPACT", "0.2"))
_MAX_AGE_HOURS     = float(os.getenv("SLEEP_RETAIN_MAX_AGE_H", "168.0"))  # 7 days


@dataclass
class RetentionPolicy:
    """Decides the fate of each memory unit in a consolidation pass."""

    keep_threshold:    float = _KEEP_THRESHOLD
    compact_threshold: float = _COMPACT_THRESHOLD
    max_age_hours:     float = _MAX_AGE_HOURS

    def decide(
        self,
        retention_score: float,
        ts: float,
        forced_keep: bool = False,
    ) -> RetentionDecision:
        """Return the retention decision for a single memory unit."""
        if forced_keep:
            return RetentionDecision.KEEP
        age_hours = (time.time() - ts) / 3600.0
        if age_hours > self.max_age_hours and retention_score < self.compact_threshold:
            return RetentionDecision.DISCARD
        if retention_score >= self.keep_threshold:
            return RetentionDecision.KEEP
        if retention_score >= self.compact_threshold:
            return RetentionDecision.COMPACT
        return RetentionDecision.DISCARD

    def classify_batch(
        self,
        items: list[dict],
        score_key: str = "retention_score",
        ts_key: str = "ts",
    ) -> dict[RetentionDecision, list[dict]]:
        """Partition *items* into keep/compact/discard bins."""
        result: dict[RetentionDecision, list[dict]] = {
            RetentionDecision.KEEP:    [],
            RetentionDecision.COMPACT: [],
            RetentionDecision.DISCARD: [],
        }
        for item in items:
            score = float(item.get(score_key, 0.5))
            ts    = float(item.get(ts_key, time.time()))
            decision = self.decide(score, ts)
            result[decision].append(item)
        return result
