from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from backend.events.models import (
    BaseEvent,
)

from production.persistence_integration.event_persistence import (
    event_persistence,
)

from runtime.observability.tracing import (
    runtime_tracer,
)


@dataclass(slots=True)
class PersistedBusEvent:
    persisted: bool
    metadata: Dict


class EventBusPersistence:
    """
    Persistent event bus wiring.
    """

    async def persist(
        self,
        event: BaseEvent,
    ) -> PersistedBusEvent:
        span = await (
            runtime_tracer
            .start_span(
                operation=(
                    "event_persist"
                ),
                correlation_id=(
                    event
                    .correlation_id
                ),
            )
        )

        archived = (
            event_persistence
            .persist(event)
        )

        await (
            runtime_tracer
            .finish_span(
                span.span_id
            )
        )

        return PersistedBusEvent(
            persisted=True,
            metadata={
                "sequence_id": (
                    archived
                    .sequence_id
                ),
            },
        )


event_bus_persistence = (
    EventBusPersistence()
)
