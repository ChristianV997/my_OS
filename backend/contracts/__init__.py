"""backend.contracts — typed artifact contracts for cross-system communication.

Every artifact produced by MarketOS or its connected repositories (ScienceR-Dsim,
KardashevOS_Level1) must be a typed dataclass that inherits from BaseArtifact.

Public surface:
    BaseArtifact       — root class with lineage fields
    SimulationArtifact — ScienceR-Dsim topology run outputs
    ResearchArtifact   — KardashevOS_Level1 synthesis outputs
    WorkflowArtifact   — MarketOS deterministic workflow outputs
    SemanticAsset      — compressed semantic units
    CampaignAsset      — campaign launch + attribution lineage
    ReplayArtifact     — replayable execution snapshots
    ArtifactRegistry   — in-memory artifact catalog
    get_registry()     → ArtifactRegistry singleton
"""
from .base       import BaseArtifact
from .simulation import SimulationArtifact
from .research   import ResearchArtifact
from .workflow   import WorkflowArtifact
from .semantic   import SemanticAsset
from .campaign   import CampaignAsset
from .replay     import ReplayArtifact
from .registry   import ArtifactRegistry, get_registry

__all__ = [
    "BaseArtifact",
    "SimulationArtifact",
    "ResearchArtifact",
    "WorkflowArtifact",
    "SemanticAsset",
    "CampaignAsset",
    "ReplayArtifact",
    "ArtifactRegistry",
    "get_registry",
]
