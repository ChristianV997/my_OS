"""backend.memory — hierarchical memory architecture.

Three tiers, matching the cognitive neuroscience model:

EPISODIC (backend/memory/episodic/)
    Raw events, execution history, replay logs.
    Highest fidelity, bounded FIFO, fast lookup.

SEMANTIC (backend/memory/semantic/)
    Compressed abstractions: hook clusters, angle archetypes, signal themes.
    Produced by consolidation runtime from episodic episodes.
    Indexed by concept label and domain.

PROCEDURAL (backend/memory/procedural/)
    Reusable workflow recipes, execution policies, scored execution strategies.
    Extracted from successful WorkflowArtifacts.
    Ranked by success_rate × avg_roas.

DO NOT build one giant shared memory. Each tier has its own store
singleton, its own fidelity contract, and its own update pathway.
"""
from .episodic   import EpisodicStore, Episode, get_episodic_store
from .semantic   import SemanticStore, SemanticUnit, get_semantic_store
from .procedural import ProceduralStore, Procedure, get_procedural_store

__all__ = [
    "EpisodicStore",   "Episode",       "get_episodic_store",
    "SemanticStore",   "SemanticUnit",  "get_semantic_store",
    "ProceduralStore", "Procedure",     "get_procedural_store",
]
