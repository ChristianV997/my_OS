from __future__ import annotations

from dataclasses import dataclass, field


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
