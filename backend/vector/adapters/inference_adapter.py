"""InferenceAdapter — index inference responses into the vector layer."""
from __future__ import annotations

from typing import Any


class InferenceAdapter:
    """Adapts InferenceResponse objects into vector records."""

    def __init__(self, creative_memory=None) -> None:
        if creative_memory is None:
            from ..memory.creative_memory import CreativeMemory
            creative_memory = CreativeMemory()
        self._cm = creative_memory

    def index_response(
        self,
        response_id: str,
        content: str,
        context: dict[str, Any],
    ) -> int:
        """Embed inference response content and index it as a creative."""
        hook    = context.get("hook", content[:80])
        product = context.get("product", "")
        roas    = float(context.get("roas", 0.0))
        return self._cm.index_creative(
            creative_id=response_id,
            hook=hook,
            product=product,
            roas=roas,
            raw_content=content[:256],
        )

    def index_hooks_from_response(self, hooks: list[str]) -> int:
        return self._cm.index_hooks(hooks)
