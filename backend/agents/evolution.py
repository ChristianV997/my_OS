import random
import copy

class StrategyEvolution:

    def __init__(self):
        self.scores = {}
        self.age = {}

    def update(self, strategy, reward):
        if strategy not in self.scores:
            self.scores[strategy] = []
            self.age[strategy] = 0

        self.scores[strategy].append(reward)
        self.age[strategy] += 1

        if len(self.scores[strategy]) > 50:
            self.scores[strategy] = self.scores[strategy][-50:]

    def survival_score(self, strategy):
        vals = self.scores.get(strategy, [])
        if not vals:
            return 0
        return sum(vals)/len(vals)

    def evolve(self, strategies):

        # compute scores
        ranked = sorted(strategies.keys(), key=lambda s: self.survival_score(s))

        # kill worst
        if len(ranked) > 2:
            worst = ranked[0]
            if self.survival_score(worst) < 0.8:
                strategies.pop(worst, None)

        # clone best
        best = ranked[-1]
        if self.survival_score(best) > 1.2:
            new_name = best + "_clone_" + str(random.randint(0,999))
            strategies[new_name] = copy.deepcopy(strategies[best])

        return strategies


evolution_engine = StrategyEvolution()
