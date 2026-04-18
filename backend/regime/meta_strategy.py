class RegimeStrategyMemory:

    def __init__(self):
        self.performance = {
            "growth": [],
            "decay": [],
            "volatile": [],
            "stable": [],
            "neutral": []
        }

    def update(self, regime, roas):
        if regime not in self.performance:
            return
        self.performance[regime].append(roas)
        if len(self.performance[regime]) > 100:
            self.performance[regime] = self.performance[regime][-100:]

    def score(self, regime):
        vals = self.performance.get(regime, [])
        if len(vals) < 5:
            return 1.0
        return sum(vals) / len(vals)


strategy_memory = RegimeStrategyMemory()
