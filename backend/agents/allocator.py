class StrategyAllocator:
    DEFAULT_STRATEGY_SCORE = 1.0

    def __init__(self):
        self.weights = {
            "conservative": 0.3,
            "aggressive": 0.4,
            "exploratory": 0.3
        }
        self.performance = {k: [] for k in self.weights}

    def update(self, strategy, reward):
        if strategy not in self.performance:
            self.performance[strategy] = []
            self.weights[strategy] = 0.3

        self.performance[strategy].append(reward)
        if len(self.performance[strategy]) > 50:
            self.performance[strategy] = self.performance[strategy][-50:]

        # recompute weights
        scores = {}
        total = 0
        for k, vals in self.performance.items():
            if len(vals) == 0:
                scores[k] = 1.0
            else:
                scores[k] = sum(vals)/len(vals)
            total += scores[k]

        if total > 0:
            for k in self.weights:
                self.weights[k] = scores.get(k, self.DEFAULT_STRATEGY_SCORE)/total

    def allocate(self, strategy, total_actions):
        return int(self.weights.get(strategy,0.3) * total_actions)

allocator = StrategyAllocator()
