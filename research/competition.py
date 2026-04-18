import random


class CompetitionAnalyzer:
    """Placeholder analyzer until live competition connectors are enabled."""

    def analyze(self, _keyword):
        return {
            "competitors": random.randint(5, 50),
            "avg_engagement": random.uniform(0.01, 0.1),
            "ad_density": random.uniform(0.1, 1.0),
        }
