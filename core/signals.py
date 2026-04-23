import random
from typing import Callable


class SignalEngine:
    """Aggregates external demand signals and scores product opportunities."""

    def __init__(self):
        self._sources: list = []

    def register_source(self, name: str, fetch_fn: Callable) -> None:
        """Register a named signal source callable."""
        self._sources.append({"name": name, "fetch": fetch_fn})

    def _mock_signals(self) -> list:
        """Fallback mock signals when no real sources are configured."""
        return [
            {
                "product": f"product_{i}",
                "score": round(random.uniform(0.3, 1.0), 2),
                "source": "mock",
                "market": "global",
                "platform": "meta",
            }
            for i in range(3)
        ]

    def get(self) -> list:
        """Fetch and aggregate signals from all registered sources."""
        if not self._sources:
            return self._mock_signals()

        all_signals: list = []
        for source in self._sources:
            try:
                signals = source["fetch"]()
                for s in signals:
                    s.setdefault("source", source["name"])
                all_signals.extend(signals)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                pass

        return all_signals if all_signals else self._mock_signals()

    def filter_opportunities(self, signals: list, min_score: float = 0.5) -> list:
        """Return only signals that meet the minimum score threshold."""
        return [s for s in signals if s.get("score", 0) >= min_score]

    def top_opportunities(self, signals: list, n: int = 5) -> list:
        """Return the top N signals by score."""
        return sorted(signals, key=lambda s: s.get("score", 0), reverse=True)[:n]


signal_engine = SignalEngine()
