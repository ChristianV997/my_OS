"""core.system.resource_allocator — allocate compute/budget resources by phase."""
from __future__ import annotations

_ALLOCATIONS: dict[str, dict[str, float]] = {
    "RESEARCH": {"research": 1.0},
    "EXPLORE": {"content": 0.5, "ads": 0.5},
    "EXPAND": {"ads": 0.7, "trading": 0.3},
    "SCALE": {"ads": 0.5, "trading": 0.4, "content": 0.1},
}


def allocate(phase: str) -> dict[str, float]:
    """Return resource allocation fractions for the given *phase*.

    Parameters
    ----------
    phase:
        Current execution phase (``"RESEARCH"``, ``"EXPLORE"``, ``"EXPAND"``,
        ``"SCALE"``).

    Returns
    -------
    dict[str, float]
        Mapping of resource category → fraction (values sum to 1.0).

    Raises
    ------
    ValueError
        If *phase* is not a recognised phase name.
    """
    if phase not in _ALLOCATIONS:
        raise ValueError(f"Unknown phase '{phase}'. Must be one of {list(_ALLOCATIONS)}")
    return dict(_ALLOCATIONS[phase])
