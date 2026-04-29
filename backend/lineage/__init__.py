"""backend.lineage — causal worldline graph and lineage tracking.

Public surface:
    get_tracker()     → LineageTracker singleton
    LineageTracker    — registers nodes, tracks worldlines, queries ancestry
    LineageGraph      — directed acyclic graph of LineageNodes
    LineageNode       — atomic causal graph unit
    Worldline         — ordered trajectory of a computational thread
    inherit_lineage() — merge parent_id lists safely
    stamp_artifact_lineage() — propagate lineage across artifact boundaries
    extract_lineage_metadata() — minimal lineage dict for event payloads
"""
from .node        import LineageNode
from .graph       import LineageGraph
from .worldline   import Worldline
from .tracker     import LineageTracker, get_tracker
from .propagation import (
    inherit_lineage,
    stamp_artifact_lineage,
    extract_lineage_metadata,
    build_lineage_chain,
)

__all__ = [
    "LineageNode",
    "LineageGraph",
    "Worldline",
    "LineageTracker",
    "get_tracker",
    "inherit_lineage",
    "stamp_artifact_lineage",
    "extract_lineage_metadata",
    "build_lineage_chain",
]
