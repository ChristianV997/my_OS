from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable

from backend.research.models.signal_event import SignalEvent


@dataclass(frozen=True)
class TrendSnapshot:
    sequence_id: int
    replay_hash: str
    topic: str
    score: float
    confidence: float
    consensus_score: float
    source_count: int
    generated_at: str
    sources: tuple[str, ...] = field(default_factory=tuple)
    top_signals: tuple[SignalEvent, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_signals(
        cls,
        *,
        topic: str,
        score: float,
        confidence: float,
        consensus_score: float,
        signals: Iterable[SignalEvent],
        metadata: dict[str, Any] | None = None,
        sequence_id: int = 0,
    ) -> "TrendSnapshot":
        signal_list = sorted(
            list(signals),
            key=lambda item: (-item.engagement, -item.velocity, item.replay_hash),
        )
        sources = tuple(sorted({item.source for item in signal_list}))
        payload = {
            "topic": topic,
            "score": round(float(score), 6),
            "confidence": round(float(confidence), 6),
            "consensus_score": round(float(consensus_score), 6),
            "sources": list(sources),
            "signals": [item.replay_hash for item in signal_list],
        }
        replay_hash = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return cls(
            sequence_id=int(sequence_id),
            replay_hash=replay_hash,
            topic=topic,
            score=round(float(score), 6),
            confidence=round(float(confidence), 6),
            consensus_score=round(float(consensus_score), 6),
            source_count=len(sources),
            generated_at=datetime.now(timezone.utc).isoformat(),
            sources=sources,
            top_signals=tuple(signal_list[:5]),
            metadata=dict(metadata or {}),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "replay_hash": self.replay_hash,
            "topic": self.topic,
            "score": self.score,
            "confidence": self.confidence,
            "consensus_score": self.consensus_score,
            "source_count": self.source_count,
            "generated_at": self.generated_at,
            "sources": list(self.sources),
            "top_signals": [item.to_record() for item in self.top_signals],
            "metadata": dict(self.metadata),
        }
