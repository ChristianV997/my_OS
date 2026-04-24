"""Data-driven creative optimization.

Stores per-creative performance metrics, ranks creatives by CTR / CVR,
clones winning variants, and discards under-performers.
"""

from __future__ import annotations


class CreativeOptimizer:
    """Ranks ad creatives by performance and generates new variants from winners.

    Metrics are keyed by ``creative_id`` (any hashable identifier).

    Usage::

        optimizer = CreativeOptimizer(ctr_threshold=0.015, cvr_threshold=0.01)
        optimizer.record("creative_1", {"ctr": 0.03, "cvr": 0.02, "clicks": 300})
        optimizer.record("creative_2", {"ctr": 0.005, "cvr": 0.001, "clicks": 50})

        winners = optimizer.winners()           # [("creative_1", {...})]
        ranked  = optimizer.rank_by_ctr()       # sorted list of (id, metrics)
        new     = optimizer.mutate(creative_1_dict)  # cloned variant
    """

    def __init__(
        self,
        ctr_threshold: float = 0.015,
        cvr_threshold: float = 0.01,
    ) -> None:
        self.ctr_threshold = ctr_threshold
        self.cvr_threshold = cvr_threshold
        # {creative_id: {ctr, cvr, clicks, conversions, ...}}
        self._metrics: dict[str, dict] = {}
        # {creative_id: creative_asset_dict}
        self._creatives: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, creative_id: str, metrics: dict) -> None:
        """Store or update performance metrics for a creative."""
        self._metrics[creative_id] = dict(metrics)

    def register(self, creative: dict) -> None:
        """Register the raw creative asset so it can be mutated later.

        The creative dict must contain an ``"id"`` key.
        """
        cid = creative.get("id")
        if cid is not None:
            self._creatives[cid] = dict(creative)

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    def rank_by_ctr(self) -> list[tuple[str, dict]]:
        """Return all tracked creatives sorted by CTR descending."""
        return sorted(
            self._metrics.items(),
            key=lambda x: x[1].get("ctr", 0.0),
            reverse=True,
        )

    def rank_by_cvr(self) -> list[tuple[str, dict]]:
        """Return all tracked creatives sorted by CVR descending."""
        return sorted(
            self._metrics.items(),
            key=lambda x: x[1].get("cvr", 0.0),
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Winner / loser classification
    # ------------------------------------------------------------------

    def winners(self) -> list[tuple[str, dict]]:
        """Return creatives that exceed both CTR and CVR thresholds."""
        return [
            (cid, m)
            for cid, m in self._metrics.items()
            if m.get("ctr", 0.0) > self.ctr_threshold
            and m.get("cvr", 0.0) > self.cvr_threshold
        ]

    def losers(self) -> list[tuple[str, dict]]:
        """Return creatives that fall below both thresholds (candidates for discard)."""
        return [
            (cid, m)
            for cid, m in self._metrics.items()
            if m.get("ctr", 0.0) <= self.ctr_threshold
            and m.get("cvr", 0.0) <= self.cvr_threshold
        ]

    def discard_losers(self) -> list[str]:
        """Remove loser creatives from tracking and return their IDs."""
        ids = [cid for cid, _ in self.losers()]
        for cid in ids:
            self._metrics.pop(cid, None)
            self._creatives.pop(cid, None)
        return ids

    # ------------------------------------------------------------------
    # Mutation / generation
    # ------------------------------------------------------------------

    def mutate(self, creative: dict) -> dict:
        """Clone a winning creative and apply a small variation.

        A suffix ``" (v<n>)"`` is appended to the headline so each
        variant is distinguishable.  The caller is responsible for
        assigning a new ``"id"`` if needed.
        """
        variation = dict(creative)
        headline = variation.get("headline", "")
        # Increment existing version tag or add (v2)
        if " (v" in headline:
            try:
                prefix, ver = headline.rsplit(" (v", 1)
                n = int(ver.rstrip(")")) + 1
                variation["headline"] = f"{prefix} (v{n})"
            except ValueError:
                variation["headline"] = headline + " (v2)"
        else:
            variation["headline"] = headline + " (v2)"
        return variation

    def generate_variants(self, count: int = 3) -> list[dict]:
        """Generate *count* new creatives by mutating each registered winner.

        Returns a flat list of mutated creative dicts.
        """
        winner_ids = {cid for cid, _ in self.winners()}
        variants: list[dict] = []
        for cid in winner_ids:
            base = self._creatives.get(cid)
            if base is None:
                continue
            for _ in range(count):
                variants.append(self.mutate(base))
        return variants
