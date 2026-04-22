import random
import copy
from backend.agents.mutation import mutate_strategy

class StrategyEvolution:

    def __init__(self):
        self.scores = {}
        self.age = {}
        self.min_strategies = 2
        self.max_strategies = 10

    def update(self, strategy, reward):
        if strategy not in self.scores:
            self.scores[strategy] = []
        if strategy not in self.age:
            self.age[strategy] = 0

        self.scores[strategy].append(reward)
        self.age[strategy] += 1

        if len(self.scores[strategy]) > 50:
            self.scores[strategy] = self.scores[strategy][-50:]

    def survival_score(self, strategy):
        vals = self.scores.get(strategy, [])
        if not vals:
            return 0
        return sum(vals) / len(vals)

    def diversity_score(self, strategies):
        # simple proxy: number of unique strategy names (can be extended later)
        return len(set(strategies.keys()))

    def mutation_strength(self, strategy, confidence=1.0):
        confidence = max(0.05, min(1.0, confidence))
        vals = self.scores.get(strategy, [])
        if len(vals) < 5:
            return 1.0 + (1.0 - confidence) * 0.4
        var = max(0.01, sum((x - sum(vals)/len(vals))**2 for x in vals)/len(vals))
        if var > 0.2:
            base = 1.2  # unstable → explore more
        else:
            base = 0.9  # stable → refine
        return base + (1.0 - confidence) * 0.2

    def evolve(self, strategies, confidence=1.0):
        confidence = max(0.05, min(1.0, confidence))

        if not strategies:
            return strategies

        ranked = sorted(strategies.keys(), key=lambda s: self.survival_score(s))

        # enforce max size (kill weakest)
        while len(strategies) > self.max_strategies:
            worst = ranked.pop(0)
            strategies.pop(worst, None)
            self.scores.pop(worst, None)
            self.age.pop(worst, None)

        # selective kill (but preserve minimum diversity)
        if len(strategies) > self.min_strategies:
            worst = ranked[0]
            if self.survival_score(worst) < (0.9 - 0.2 * (1.0 - confidence)):
                strategies.pop(worst, None)
                self.scores.pop(worst, None)
                self.age.pop(worst, None)

        # clone best with mutation
        best = ranked[-1]
        clone_threshold = 1.2 - 0.3 * (1.0 - confidence)
        if self.survival_score(best) > clone_threshold and len(strategies) < self.max_strategies:
            new_name = f"{best}_clone_{random.randint(0,999)}"

            # prevent over-cloning identical structures
            if new_name not in strategies:
                try:
                    cloned = copy.deepcopy(strategies[best])

                    # apply mutation scaling
                    strength = self.mutation_strength(best, confidence=confidence)
                    if strength >= 1.35:
                        mutate_steps = 2
                    elif strength >= 1.1:
                        mutate_steps = 2
                    else:
                        mutate_steps = 1
                    mutated = cloned
                    # repeated mutation is intentional: lower confidence increases
                    # cumulative exploration pressure on cloned strategies
                    for _ in range(mutate_steps):
                        mutated = mutate_strategy(mutated)

                    strategies[new_name] = mutated
                except Exception:
                    pass

        return strategies


evolution_engine = StrategyEvolution()
