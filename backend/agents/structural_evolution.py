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


def blend_multi(weights_list):
    keys = weights_list[0].keys()
    return {k: sum(w[k] for w in weights_list) / len(weights_list) for k in keys}


def mutate_structure(structure, global_knowledge=None, intensity=0.1):
    s = copy.deepcopy(structure)
    s["id"] = _new_id()
    s["parent_id"] = structure.get("id")

    # blend parent + global knowledge
    if global_knowledge:
        s["weights"] = blend_multi([structure["weights"], global_knowledge["weights"]])

        for f in s["features"]:
            if random.random() < 0.5:
                s["features"][f] = global_knowledge["features"].get(f, s["features"][f])

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
    s["memory"] = structure.get("memory", {}).copy()

    return s


class StructuralEvolution:
    def __init__(self):
        self.population = []
        self.scores = defaultdict(list)
        self.lineage_scores = defaultdict(list)
        self.global_knowledge = None

    def initialize(self, n=5):
        self.population = [random_structure() for _ in range(n)]

    def score(self, structure, performance):
        sid = structure.get("id")
        pid = structure.get("parent_id")

        self.scores[sid].append(performance)

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

    def select_best(self, top_k=3):
        ranked = []
        for s in self.population:
            sid = s.get("id")
            score = self.avg_score(sid) + 0.5 * self.lineage_score(sid)
            ranked.append((s, score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in ranked[:top_k]]

    def distill_global_knowledge(self):
        best = self.select_best()
        if not best:
            return

        weights = [s["weights"] for s in best]
        features = defaultdict(int)

        for s in best:
            for f, v in s["features"].items():
                if v:
                    features[f] += 1

        self.global_knowledge = {
            "weights": blend_multi(weights),
            "features": {f: features[f] / len(best) > 0.5 for f in STRUCTURE_SPACE["features"]}
        }

    def evolve(self):
        self.distill_global_knowledge()
        best = self.select_best()
        new_pop = []

        for b in best:
            new_pop.append(b)
            for _ in range(3):
                new_pop.append(mutate_structure(b, self.global_knowledge))

        self.population = new_pop[:10]


structural_engine = StructuralEvolution()
