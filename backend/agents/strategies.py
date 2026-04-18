import random

class BaseStrategy:
    def propose(self, state):
        raise NotImplementedError


class ConservativeStrategy(BaseStrategy):
    def propose(self, state):
        # low variance, safe actions
        return [{"variant": random.randint(1,2), "intensity": 0.3} for _ in range(2)]


class AggressiveStrategy(BaseStrategy):
    def propose(self, state):
        # high risk / high reward
        return [{"variant": random.randint(3,5), "intensity": 1.0} for _ in range(3)]


class ExploratoryStrategy(BaseStrategy):
    def propose(self, state):
        # random exploration
        return [{"variant": random.randint(1,5), "intensity": random.uniform(0.1,1.0)} for _ in range(4)]


strategies = {
    "conservative": ConservativeStrategy(),
    "aggressive": AggressiveStrategy(),
    "exploratory": ExploratoryStrategy()
}
