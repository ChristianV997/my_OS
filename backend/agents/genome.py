import random

class StrategyGenome:

    def __init__(self,
                 risk_level=0.5,
                 exploration_rate=0.3,
                 intensity_range=(0.2,1.0),
                 variant_bias=3):

        self.risk_level = risk_level
        self.exploration_rate = exploration_rate
        self.intensity_range = intensity_range
        self.variant_bias = variant_bias

    def mutate(self, strength=1.0):

        self.risk_level = min(1.0, max(0.0, self.risk_level * random.uniform(0.8,1.2*strength)))
        self.exploration_rate = min(1.0, max(0.0, self.exploration_rate * random.uniform(0.8,1.2*strength)))

        low, high = self.intensity_range
        low *= random.uniform(0.9,1.1*strength)
        high *= random.uniform(0.9,1.1*strength)
        self.intensity_range = (max(0.05, low), min(1.5, high))

        self.variant_bias = int(min(5, max(1, self.variant_bias + random.choice([-1,0,1]))))

        return self
