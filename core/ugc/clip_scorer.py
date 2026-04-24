from collections import defaultdict


class ClipScorer:
    """Track average ROAS per UGC clip and surface the top performers."""

    def __init__(self):
        self.scores: dict[str, list[float]] = defaultdict(list)

    def update(self, clip_id: str, roas: float) -> None:
        self.scores[clip_id].append(roas)

    def get_score(self, clip_id: str) -> float:
        values = self.scores.get(clip_id, [])
        if not values:
            return 0.0
        return sum(values) / len(values)

    def top_clips(self, k: int = 5) -> list[tuple[str, float]]:
        ranked = sorted(
            [(cid, self.get_score(cid)) for cid in self.scores],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:k]
