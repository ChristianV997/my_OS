"""Internal utilities shared across the inference package."""
from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models.inference_request import InferenceRequest


def compute_replay_hash(request: "InferenceRequest") -> str:
    """SHA-256 fingerprint of the request *content* (not sequence_id).

    Two requests with identical prompt/model/temperature/seed produce the
    same hash regardless of their sequence_id.  Used to detect replay hits
    and to tag InferenceResponse for the event log.
    """
    sig = json.dumps(
        {
            "prompt":      request.prompt,
            "model":       request.model,
            "system":      request.system,
            "temperature": request.temperature,
            "max_tokens":  request.max_tokens,
            "seed":        request.seed,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(sig.encode()).hexdigest()[:16]


def now_ms() -> float:
    """Monotonic elapsed milliseconds — use for latency measurements."""
    return time.monotonic() * 1000
