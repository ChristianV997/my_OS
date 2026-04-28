"""Streaming support — wraps provider generators with telemetry and replay safety.

Usage:
    from backend.inference.streaming import stream_complete

    for chunk in stream_complete(request):
        print(chunk, end="", flush=True)
    # After iteration, stream_complete returns an InferenceResponse via StopIteration.

WebSocket compatibility:
    Chunks are plain strings.  The WebSocket handler yields each chunk as a
    JSON frame:  {"type": "inference.chunk", "content": chunk, "seq": i, ...}
    The final frame includes the full InferenceResponse payload.
"""
from __future__ import annotations

import logging
import time
from typing import Generator

from .models.inference_request  import InferenceRequest
from .models.inference_response import InferenceResponse

_log = logging.getLogger(__name__)


class StreamHandle:
    """Accumulates chunks and produces a final InferenceResponse."""

    def __init__(self, request: InferenceRequest, provider_name: str) -> None:
        self.request       = request
        self.provider_name = provider_name
        self._chunks:  list[str] = []
        self._start_ms = time.monotonic() * 1000
        self.chunk_count = 0

    def feed(self, chunk: str) -> str:
        self._chunks.append(chunk)
        self.chunk_count += 1
        return chunk

    def finalize(self) -> InferenceResponse:
        from ._utils import compute_replay_hash
        content = "".join(self._chunks)
        return InferenceResponse(
            content=content,
            provider=self.provider_name,
            model="streaming",
            sequence_id=self.request.sequence_id,
            replay_hash=compute_replay_hash(self.request),
            latency_ms=time.monotonic() * 1000 - self._start_ms,
            prompt_tokens=len(self.request.prompt.split()),
            completion_tokens=len(content.split()),
        )


def stream_complete(
    request: InferenceRequest,
    router=None,
) -> Generator[str, None, InferenceResponse]:
    """Convenience wrapper that calls router.stream() with telemetry.

    Yields token chunks.  Returns InferenceResponse via StopIteration.value.
    The response is also stored in the router cache for replay safety.
    """
    if router is None:
        from .router import get_router
        router = get_router()

    gen      = router.stream(request)
    response = None
    try:
        while True:
            yield next(gen)
    except StopIteration as stop:
        response = stop.value

    return response


def stream_to_websocket(
    request:    InferenceRequest,
    send_fn,                        # Callable[[dict], None] — WS send
    router=None,
) -> InferenceResponse | None:
    """Stream tokens to a WebSocket, emitting structured JSON frames.

    send_fn({"type": "inference.chunk", "content": chunk, "seq": i, "seq_id": ...})
    Final frame: {"type": "inference.done", "response": response.to_dict()}
    """
    seq      = 0
    response = None
    try:
        gen = stream_complete(request, router=router)
        try:
            while True:
                chunk = next(gen)
                send_fn({
                    "type":       "inference.chunk",
                    "content":    chunk,
                    "seq":        seq,
                    "sequence_id": request.sequence_id,
                })
                seq += 1
        except StopIteration as stop:
            response = stop.value
    except Exception as exc:
        _log.error("ws_stream_error seq=%s error=%s", request.sequence_id, exc)

    if response:
        send_fn({
            "type":     "inference.done",
            "response": response.to_dict(),
        })
    return response
