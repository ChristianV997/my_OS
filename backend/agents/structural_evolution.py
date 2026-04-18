import random
import copy
import uuid
from collections import defaultdict

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


def _new_id():
    return str(uuid.uuid4())[:8]


def random_structure():
    return {
        "id": _new_id(),
        "parent_id": None,
        "weights": {k: random.uniform(*v) for k, v in STRUCTURE_SPACE["weights"].items()},
        "features": {f: random.choice([True, False]) for f in STRUCTURE_SPACE["features"]},
        "planning_depth": random.randint(*STRUCTURE_SPACE["planning_depth"]),
        "memory": {"avg_perf": 0.0, "count": 0}
    }


def blend_weights(a, b, alpha=0.3):
    return {k: (1 - alpha) * a[k] + alpha * b[k] for k in a}


def mutate_structure(structure, global_best=None, intensity=0.1):
    s = copy.deepcopy(structure)
    s["id"] = _new_id()
    s["parent_id"] = structure.get("id")

    # blend with global best
    if global_best:
        s["weights"] = blend_weights(structure["weights"], global_best["weights"], alpha=0.3)

    for k in s["weights"]:
        if random.random() < 0.5:
            delta = random.uniform(-intensity, intensity)
            s["weights"][k] = max(0.0, s["weights"][k] + delta)

    for f in s["features"]:
        if random.random() < 0.2:
            s["features"][f] = not s["features"][f]

    if random.random() < 0.3:
        delta = random.choice([-1, 1])
        s["planning_depth"] = max(1, min(5, s["planning_depth"] + delta))

    # inherit memory
    parent_mem = structure.get("memory", {"avg_perf": 0.0, "count": 0})
    s["memory"] = parent_mem.copy()

    return s


class StructuralEvolution:
    def __init__(self):
        self.population = []
        self.scores = defaultdict(list)
        self.lineage_scores = defaultdict(list)

    def initialize(self, n=5):
        self.population = [random_structure() for _ in range(n)]

    def score(self, structure, performance):
        sid = structure.get("id")
        pid = structure.get("parent_id")

        self.scores[sid].append(performance)

        # update memory
        mem = structure.setdefault("memory", {"avg_perf": 0.0, "count": 0})
        mem["count"] += 1
        mem["avg_perf"] = (mem["avg_perf"] * (mem["count"] - 1) + performance) / mem["count"]

        if pid:
            self.lineage_scores[pid].append(performance)

    def avg_score(self, sid):
        vals = self.scores.get(sid, [])
        return sum(vals)/len(vals) if vals else 0

    def lineage_score(self, sid):
        vals = self.lineage_scores.get(sid, [])
        return sum(vals)/len(vals) if vals else 0

    def select_best(self, top_k=2):
        ranked = []
        for s in self.population:
            sid = s.get("id")
            score = self.avg_score(sid) + 0.5 * self.lineage_score(sid)
            ranked.append((s, score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in ranked[:top_k]]

    def global_best(self):
        best = self.select_best(1)
        return best[0] if best else None

    def evolve(self):
        best = self.select_best()
        gbest = self.global_best()
        new_pop = []

        for b in best:
            new_pop.append(b)
            for _ in range(3):
                new_pop.append(mutate_structure(b, global_best=gbest))

        self.population = new_pop[:10]


structural_engine = StructuralEvolution()
