from collections import defaultdict


class SequenceOptimizer:
    """Track average ROAS per ad sequence and surface the best orderings."""

    def __init__(self):
        self.sequence_scores: dict[str, list[float]] = defaultdict(list)

    def update(self, sequence_id: str, roas: float) -> None:
        self.sequence_scores[sequence_id].append(roas)

    def best_sequences(self, k: int = 3) -> list[tuple[str, float]]:
        ranked = sorted(
            [
                (sid, sum(v) / len(v))
                for sid, v in self.sequence_scores.items()
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:k]
