"""CompressionPolicy — when and how to compress episodic memory into semantic units.

Controls the cluster count, minimum cluster size, and similarity threshold
used during semantic compression.  Tuned for consumer hardware (no GPU).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


_MIN_EPISODES_TO_COMPRESS = int(os.getenv("SLEEP_COMPRESS_MIN_EPISODES", "10"))
_MAX_CLUSTERS             = int(os.getenv("SLEEP_COMPRESS_MAX_CLUSTERS", "8"))
_MIN_CLUSTER_SIZE         = int(os.getenv("SLEEP_COMPRESS_MIN_CLUSTER_SIZE", "3"))
_SIMILARITY_THRESHOLD     = float(os.getenv("SLEEP_COMPRESS_SIM_THRESHOLD", "0.75"))
_MAX_LINEAGE_DEPTH        = int(os.getenv("SLEEP_COMPRESS_MAX_LINEAGE_DEPTH", "100"))


@dataclass
class CompressionPolicy:
    """Controls semantic compression and lineage summarization behavior."""

    min_episodes_to_compress: int   = _MIN_EPISODES_TO_COMPRESS
    max_clusters:             int   = _MAX_CLUSTERS
    min_cluster_size:         int   = _MIN_CLUSTER_SIZE
    similarity_threshold:     float = _SIMILARITY_THRESHOLD
    max_lineage_depth:        int   = _MAX_LINEAGE_DEPTH

    def should_compress(self, episode_count: int) -> bool:
        return episode_count >= self.min_episodes_to_compress

    def cluster_count(self, episode_count: int) -> int:
        """Heuristic: sqrt(n) clusters capped at max_clusters."""
        import math
        return min(self.max_clusters, max(2, int(math.sqrt(episode_count))))

    def should_summarize_lineage(self, depth: int) -> bool:
        return depth > self.max_lineage_depth

    def cluster_is_significant(self, cluster_size: int) -> bool:
        return cluster_size >= self.min_cluster_size
