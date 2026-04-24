import numpy as np


class CausalModel:
    def __init__(self):
        self.weights = {
            "price": -0.5,
            "creative": 0.3,
            "budget": 0.4,
        }

    def estimate_effect(self, action):
        effect = 0
        for k, v in action.items():
            if k in self.weights:
                effect += self.weights[k] * v
        return effect
