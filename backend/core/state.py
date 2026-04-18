from backend.data.event_log import EventLog
from backend.causal.graph import CausalGraph


class SystemState:

    def __init__(self):
        self.event_log = EventLog()
        self.graph = CausalGraph()
        self.energy = {"fatigue": 0.1, "load": 0.2}
        self.population = []
        self.regime = "neutral"
        self.detected_regime = "unknown"
        self.capital = 1000.0
        self.memory = []
        self.total_cycles = 0
        self.causal_insights = {}
