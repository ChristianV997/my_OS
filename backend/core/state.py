from backend.data.event_log import EventLog
from backend.causal.graph import CausalGraph

DEFAULT_FATIGUE = 0.1
DEFAULT_LOAD = 0.2
DEFAULT_CAPITAL = 1000.0


class SystemState:

    def __init__(self):
        self.event_log = EventLog()
        self.graph = CausalGraph()
        self.energy = {"fatigue": DEFAULT_FATIGUE, "load": DEFAULT_LOAD}
        self.population = []
        self.regime = "neutral"
        self.detected_regime = "unknown"
        self.capital = DEFAULT_CAPITAL
        self.memory = []
        self.total_cycles = 0
        self.last_reality_gap = None
        self.last_confidence = 1.0
        self.last_heal_actions = []


def ensure_state_shape(state):
    if not hasattr(state, "event_log") or state.event_log is None:
        state.event_log = EventLog()
    if not hasattr(state.event_log, "rows"):
        state.event_log.rows = []

    if not hasattr(state, "graph") or state.graph is None:
        state.graph = CausalGraph()
    if not hasattr(state.graph, "edges"):
        state.graph.edges = {}

    if not hasattr(state, "energy") or not isinstance(state.energy, dict):
        state.energy = {"fatigue": DEFAULT_FATIGUE, "load": DEFAULT_LOAD}
    if not hasattr(state, "population") or state.population is None:
        state.population = []
    if not hasattr(state, "regime"):
        state.regime = "neutral"
    if not hasattr(state, "detected_regime"):
        state.detected_regime = "unknown"
    if not hasattr(state, "capital"):
        state.capital = DEFAULT_CAPITAL
    if not hasattr(state, "memory") or state.memory is None:
        state.memory = []
    if not hasattr(state, "total_cycles"):
        state.total_cycles = 0
    if not hasattr(state, "last_reality_gap"):
        state.last_reality_gap = None
    if not hasattr(state, "last_confidence"):
        state.last_confidence = 1.0
    if not hasattr(state, "last_heal_actions") or state.last_heal_actions is None:
        state.last_heal_actions = []

    return state
