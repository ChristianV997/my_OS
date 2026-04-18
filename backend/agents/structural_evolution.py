import random
import copy

STRUCTURE_SPACE = {
    "weights": {
        "world_model": (0.1, 1.0),
        "causal": (0.0, 1.0),
        "velocity": (0.0, 1.0),
        "advantage": (0.0, 1.0),
    },
    "features": [
        "use_causal",
        "use_velocity",
        "use_advantage",
        "use_regime",
    ],
    "planning_depth": (1, 5)
}


def random_structure():
    return {
        "weights": {k: random.uniform(*v) for k, v in STRUCTURE_SPACE["weights"].items()},
        "features": {f: random.choice([True, False]) for f in STRUCTURE_SPACE["features"]},
        "planning_depth": random.randint(*STRUCTURE_SPACE["planning_depth"])
    }


def mutate_structure(structure, intensity=0.1):
    s = copy.deepcopy(structure)

    # mutate weights
    for k in s["weights"]:
        if random.random() < 0.5:
            delta = random.uniform(-intensity, intensity)
            s["weights"][k] = max(0.0, s["weights"][k] + delta)

    # mutate features
    for f in s["features"]:
        if random.random() < 0.2:
            s["features"][f] = not s["features"][f]

    # mutate planning depth
    if random.random() < 0.3:
        delta = random.choice([-1, 1])
        s["planning_depth"] = max(1, min(5, s["planning_depth"] + delta))

    return s


class StructuralEvolution:
    def __init__(self):
        self.population = []
        self.scores = {}

    def initialize(self, n=5):
        self.population = [random_structure() for _ in range(n)]

    def score(self, structure, performance):
        key = str(structure)
        self.scores.setdefault(key, []).append(performance)

    def select_best(self, top_k=2):
        avg_scores = [
            (s, sum(v)/len(v))
            for s, v in self.scores.items()
        ]
        avg_scores.sort(key=lambda x: x[1], reverse=True)
        return [eval(s) for s, _ in avg_scores[:top_k]]

    def evolve(self):
        best = self.select_best()
        new_pop = []

        for b in best:
            new_pop.append(b)
            for _ in range(2):
                new_pop.append(mutate_structure(b))

        self.population = new_pop[:10]


structural_engine = StructuralEvolution()
