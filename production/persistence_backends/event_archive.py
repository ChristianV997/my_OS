from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List


ARCHIVE_PATH = Path(
    "backend/state/event_archive.jsonl"
)


@dataclass(slots=True)
class ArchivedEvent:
    sequence_id: int
    event_type: str
    payload: Dict
    correlation_id: str | None
    timestamp: float


class EventArchive:
    """
    Append-only replay-safe event archive.
    """

    def __init__(self):
        self.sequence = 0

        ARCHIVE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def append(
        self,
        *,
        event_type: str,
        payload: Dict,
        correlation_id: str | None,
    ) -> ArchivedEvent:
        event = ArchivedEvent(
            sequence_id=self.sequence,
            event_type=event_type,
            payload=payload,
            correlation_id=(
                correlation_id
            ),
            timestamp=time.time(),
        )

        with ARCHIVE_PATH.open(
            "a"
        ) as f:
            f.write(
                json.dumps(
                    asdict(event)
                )
                + "\n"
            )

        self.sequence += 1

        return event

    def replay(
        self,
    ) -> List[
        ArchivedEvent
    ]:
        if not ARCHIVE_PATH.exists():
            return []

        events = []

        for line in (
            ARCHIVE_PATH
            .read_text()
            .splitlines()
        ):
            if not line.strip():
                continue

            events.append(
                ArchivedEvent(
                    **json.loads(
                        line
                    )
                )
            )

        return events


event_archive = EventArchive()
