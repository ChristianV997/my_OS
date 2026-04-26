"""simulation — pre-execution scoring and ranking layer.

Sits between discovery and execution: scores signals, niches, hooks, and
creatives using historical replay + a Ridge-based engagement model before
any real spend is committed.
"""
from simulation.engine import SimulationEngine, simulation_engine

__all__ = ["SimulationEngine", "simulation_engine"]
