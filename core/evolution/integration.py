"""core.evolution.integration — thin wrapper around the backend evolution engine.

Delegates to ``backend.agents.structural_evolution`` so the core engine layer
shares one evolution implementation.
"""
from __future__ import annotations

from typing import Any

from backend.agents.structural_evolution import structural_engine as _engine


def evolve(agents: dict[str, Any], env: dict[str, Any]) -> dict[str, Any]:
    """Run one evolution cycle over *agents* given the current *env*.

    Parameters
    ----------
    agents:
        Mapping of agent_id → genome / strategy dict.
    env:
        Environment snapshot (e.g. regime, ROAS, spend).

    Returns
    -------
    dict
        Updated agents mapping (population after evolve()).
    """
    roas = env.get("roas", 1.0)
    for genome in agents.values():
        _engine.score(genome, roas)

    new_population = _engine.evolve()
    if isinstance(new_population, list):
        return {s["id"]: s for s in new_population if isinstance(s, dict) and "id" in s}
    return agents
