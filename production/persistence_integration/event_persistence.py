from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from backend.events.models import (
    BaseEvent,
)

from production.persistence_backends.event_archive import (
    event_archive,
)


@dataclass(slots=True)
class PersistedEvent:
    archived: bool
    sequence_id: int
    metadata: Dict


class EventPersistence:
    """
    Automatic runtime event archival.
    """

    def persist(
        self,
        event: BaseEvent,
    ) -> PersistedEvent:
        archived = (
            event_archive
            .append(
                event_type=str(
                    event.event_type
                ),
                payload=event.payload,
                correlation_id=(
                    event
                    .correlation_id
                ),
            )
        )

        return PersistedEvent(
            archived=True,
            sequence_id=(
                archived.sequence_id
            ),
            metadata={
                "event_type": str(
                    event.event_type
                ),
            },
        )


event_persistence = (
    EventPersistence()
)
