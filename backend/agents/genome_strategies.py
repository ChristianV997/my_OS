import random
from backend.agents.genome import StrategyGenome

class GenomeStrategy:

    def __init__(self, genome=None):
        self.genome = genome or StrategyGenome()

    def propose(self, state):

        actions = []
        n = int(3 + self.genome.exploration_rate * 5)

        for _ in range(n):

            if random.random() < self.genome.exploration_rate:
                variant = random.randint(1,5)
            else:
                variant = self.genome.variant_bias

            low, high = self.genome.intensity_range
            intensity = random.uniform(low, high) * (1 + self.genome.risk_level)

            actions.append({
                "variant": variant,
                "intensity": intensity
            })

        return actions


def create_initial_strategies():
    return {
        "genome_1": GenomeStrategy(),
        "genome_2": GenomeStrategy(),
        "genome_3": GenomeStrategy()
    }
