from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping

from backend.research.scoring.topic_normalizer import normalize_topic


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _stable_hash(*parts: Any) -> str:
    return sha256(_canonical_json(parts).encode("utf-8")).hexdigest()


def _normalize_float(value: float | int | None) -> float:
    try:
        return round(float(value or 0.0), 6)
    except (TypeError, ValueError):
        return 0.0


def _normalize_timestamp(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    return str(value)


@dataclass(frozen=True)
class SignalEvent:
    sequence_id: int
    replay_hash: str
    source: str
    topic: str
    engagement: float
    velocity: float
    confidence: float
    freshness_ts: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    dedupe_key: str = ""

    @classmethod
    def from_payload(
        cls,
        *,
        source: str,
        topic: str,
        engagement: float | int,
        velocity: float | int,
        confidence: float | int,
        freshness_ts: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        sequence_id: int = 0,
    ) -> "SignalEvent":
        normalized_topic = normalize_topic(topic)
        normalized_metadata = dict(metadata or {})
        ts = _normalize_timestamp(freshness_ts)
        engagement_value = _normalize_float(engagement)
        velocity_value = _normalize_float(velocity)
        confidence_value = min(1.0, max(0.0, _normalize_float(confidence)))
        replay_hash = _stable_hash(
            source.strip().lower(),
            normalized_topic,
            engagement_value,
            velocity_value,
            confidence_value,
            ts,
            normalized_metadata,
        )
        dedupe_key = f"{source.strip().lower()}:{normalized_topic}:{ts[:13]}"
        return cls(
            sequence_id=int(sequence_id or 0),
            replay_hash=replay_hash,
            source=source.strip().lower(),
            topic=normalized_topic,
            engagement=engagement_value,
            velocity=velocity_value,
            confidence=confidence_value,
            freshness_ts=ts,
            metadata=normalized_metadata,
            dedupe_key=dedupe_key,
        )

    def with_sequence(self, sequence_id: int) -> "SignalEvent":
        return SignalEvent(
            sequence_id=int(sequence_id),
            replay_hash=self.replay_hash,
            source=self.source,
            topic=self.topic,
            engagement=self.engagement,
            velocity=self.velocity,
            confidence=self.confidence,
            freshness_ts=self.freshness_ts,
            metadata=dict(self.metadata),
            dedupe_key=self.dedupe_key,
        )

    def to_record(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metadata"] = dict(self.metadata)
        return payload

    def to_storage_payload(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "replay_hash": self.replay_hash,
            "source": self.source,
            "topic": self.topic,
            "engagement": self.engagement,
            "velocity": self.velocity,
            "confidence": self.confidence,
            "freshness_ts": self.freshness_ts,
            "metadata_json": _canonical_json(dict(self.metadata)),
            "dedupe_key": self.dedupe_key,
        }
