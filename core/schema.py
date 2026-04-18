from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_type: str
    timestamp: datetime

    product_id: str
    product_name: str

    hook: str | None = None
    angle: str | None = None

    spend: float = 0.0
    revenue: float = 0.0
    roas: float = 0.0

    ctr: float = 0.0
    cvr: float = 0.0

    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
