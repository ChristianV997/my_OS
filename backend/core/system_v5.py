import json
import os

from backend.agents.genome_strategies import create_initial_strategies
from backend.agents.allocator import allocator
from backend.agents.evolution import evolution_engine
from backend.core.state import SystemState
from backend.learning.campaign_learning import campaign_learning

STATE_PATH = "backend/state/system_state.json"


def _json_default(obj):
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except (TypeError, ValueError):
            pass
    if hasattr(obj, "__float__"):
        try:
            return float(obj)
        except (TypeError, ValueError):
            pass
    if hasattr(obj, "__int__"):
        try:
            return int(obj)
        except (TypeError, ValueError):
            pass
    return str(obj)


def _normalize_for_json(value):
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            normalized_key = _normalize_for_json(key)
            if not isinstance(normalized_key, (str, int, float, bool, type(None))):
                normalized_key = str(normalized_key)
            normalized[normalized_key] = _normalize_for_json(item)
        return normalized
    if isinstance(value, set):
        try:
            items = sorted(value, key=str)
        except TypeError:
            items = list(value)
        return [_normalize_for_json(item) for item in items]
    if isinstance(value, (list, tuple)):
        return [_normalize_for_json(item) for item in value]
    if hasattr(value, "item"):
        try:
            item_value = value.item()
            # Guard against scalar-like objects whose .item() returns self.
            if item_value is value:
                return str(value)
            return _normalize_for_json(item_value)
        except (TypeError, ValueError):
            return value
    return value


class PersistentState(SystemState):

    def __init__(self):
        super().__init__()
        self.strategies = create_initial_strategies()
        self.step = 0

    def save(self):
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)

        data = _normalize_for_json({
            "capital": self.capital,
            "memory": self.memory,
            "total_cycles": self.total_cycles,
            "regime": self.regime,
            "detected_regime": self.detected_regime,
            "energy": self.energy,
            "population": self.population,
            "event_log_rows": self.event_log.rows,
            "graph_edges": [
                [parent, child, weight]
                for (parent, child), weight in self.graph.edges.items()
            ],
            "step": self.step,
            "allocator_weights": allocator.weights,
            "evolution_scores": evolution_engine.scores,
            "strategies": {
                name: s.genome.__dict__
                for name, s in self.strategies.items()
            }
        })

        with open(STATE_PATH, "w") as f:
            json.dump(data, f, default=_json_default)

    def load(self):
        if not os.path.exists(STATE_PATH):
            return

        with open(STATE_PATH, "r") as f:
            data = json.load(f)

        self.capital = data.get("capital", self.capital)
        self.memory = data.get("memory", self.memory)
        self.total_cycles = data.get("total_cycles", self.total_cycles)
        self.regime = data.get("regime", self.regime)
        self.detected_regime = data.get("detected_regime", self.detected_regime)
        self.energy = data.get("energy", self.energy)
        self.population = data.get("population", self.population)
        self.event_log.rows = data.get("event_log_rows", self.event_log.rows)

        for edge in data.get("graph_edges", []):
            if len(edge) != 3:
                continue
            parent, child, weight = edge
            self.graph.add_edge(parent, child, weight)

        self.step = data.get("step", 0)

        allocator.weights.update(data.get("allocator_weights", {}))
        evolution_engine.scores.update(data.get("evolution_scores", {}))

        # restore strategies
        restored = {}
        for name, genome_data in data.get("strategies", {}).items():
            from backend.agents.genome import StrategyGenome
            from backend.agents.genome_strategies import GenomeStrategy

            genome = StrategyGenome(**genome_data)
            restored[name] = GenomeStrategy(genome)

        if restored:
            self.strategies.clear()
            self.strategies.update(restored)


class SystemV5:

    def __init__(self):
        self.state = PersistentState()
        self.state.load()

    def run_cycle(self, env, decision_engine):

        self.state.step += 1

        decisions = decision_engine(self.state)

        results = []

        for d in decisions[:5]:
            outcome = env.execute(d["action"])
            outcome["prediction"] = d.get("pred", 1.0)
            outcome["strategy"] = d.get("strategy")
            campaign_id = d.get("campaign_id")
            if not campaign_id:
                campaign_id = d["action"].get("campaign_id")
            if not campaign_id:
                campaign_id = "default_campaign"
            outcome["campaign_id"] = campaign_id

            allocator.update(d["strategy"], outcome.get("roas", 0))
            evolution_engine.update(d["strategy"], outcome.get("roas", 0))
            campaign_learning.update(d["action"], outcome)

            results.append(outcome)

        if results:
            self.state.event_log.log_batch(results)

        # long-term evolution
        if self.state.step % 10 == 0:
            evolved = evolution_engine.evolve(self.state.strategies)
            if evolved is not self.state.strategies:
                self.state.strategies.clear()
                self.state.strategies.update(evolved)

        self.state.save()

        return results
