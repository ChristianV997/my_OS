from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CampaignArtifact:
    """Serializable record of a launched campaign with full attribution lineage.

    Created at launch time by _run_scaling() and stored in _campaign_artifacts.
    Consumed by _run_metrics_ingestion() to pair real ROAS back to the hook
    and angle that drove the campaign, closing the metrics→PatternStore loop.
    """
    campaign_id:    str
    adgroup_id:     str
    ad_ids:         list[str]
    product:        str
    hook:           str
    angle:          str
    phase:          str
    estimated_roas: float
    budget:         float
    launched_at:    float = field(default_factory=time.time)
    dry_run:        bool  = True

    def to_dict(self) -> dict:
        return {
            "campaign_id":    self.campaign_id,
            "adgroup_id":     self.adgroup_id,
            "ad_ids":         self.ad_ids,
            "product":        self.product,
            "hook":           self.hook,
            "angle":          self.angle,
            "phase":          self.phase,
            "estimated_roas": self.estimated_roas,
            "budget":         self.budget,
            "launched_at":    self.launched_at,
            "dry_run":        self.dry_run,
        }


@dataclass
class ContentEvent:
    creative_id: str
    product: str = ""
    hook: str = ""
    angle: str = ""
    platform: str = "tiktok"
    roas: float = 0.0
    ctr: float = 0.0
    cvr: float = 0.0
    spend: float = 0.0
    revenue: float = 0.0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    plays: int = 0
    view_duration_s: float = 0.0
    engagement_rate: float = 0.0
    label: str = "NEUTRAL"
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)
