"""backend.inference.scheduling — inference request scheduling utilities.

Provides a simple priority queue for scheduling inference requests when
multiple concurrent callers compete for provider capacity.

The scheduler is synchronous and thread-safe.  It does not manage async
event loops — the router.complete() / router.stream() methods handle that.

Design goals
------------
- Deterministic: requests with the same sequence_id are always processed in
  sequence_id order regardless of arrival order.
- Replay-safe: the scheduler never discards a request silently; every
  dequeue operation returns the next request or None.
- Observable: queue depth is exposed for telemetry / health monitoring.
"""
from __future__ import annotations

import heapq
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Iterator

from backend.inference.models.inference_request import InferenceRequest

_log = logging.getLogger(__name__)

_MAX_QUEUE_SIZE = 1000  # hard cap to prevent unbounded growth


@dataclass(order=True)
class _ScheduledItem:
    """Priority queue item.  Sorts by (priority, sequence_id, ts)."""

    priority: int
    sequence_id: int
    ts: float
    request: InferenceRequest = field(compare=False)


class InferenceScheduler:
    """Thread-safe priority scheduler for InferenceRequests.

    Priority levels
    ---------------
    0  — critical (highest priority)
    1  — high
    2  — normal (default)
    3  — low
    """

    def __init__(self, max_size: int = _MAX_QUEUE_SIZE) -> None:
        self._heap: list[_ScheduledItem] = []
        self._lock = threading.Lock()
        self._max_size = max_size
        self._counter = 0  # monotonic sequence for requests without sequence_id

    def enqueue(
        self,
        request: InferenceRequest,
        priority: int = 2,
    ) -> bool:
        """Add a request to the scheduling queue.

        Returns True if enqueued successfully, False if the queue is full.
        """
        with self._lock:
            if len(self._heap) >= self._max_size:
                _log.warning(
                    "inference_scheduler_queue_full max=%d request_id=%s",
                    self._max_size,
                    request.request_id,
                )
                return False

            self._counter += 1
            seq = request.sequence_id if request.sequence_id is not None else self._counter
            item = _ScheduledItem(
                priority=priority,
                sequence_id=seq,
                ts=request.ts or time.time(),
                request=request,
            )
            heapq.heappush(self._heap, item)
            return True

    def dequeue(self) -> InferenceRequest | None:
        """Remove and return the highest-priority request, or None if empty."""
        with self._lock:
            if not self._heap:
                return None
            return heapq.heappop(self._heap).request

    def peek(self) -> InferenceRequest | None:
        """Return the next request without removing it."""
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0].request

    def drain(self) -> Iterator[InferenceRequest]:
        """Yield all queued requests in priority order (empties the queue)."""
        while True:
            req = self.dequeue()
            if req is None:
                break
            yield req

    @property
    def depth(self) -> int:
        """Current number of requests in the queue."""
        with self._lock:
            return len(self._heap)

    def clear(self) -> int:
        """Remove all queued requests.  Returns the count removed."""
        with self._lock:
            n = len(self._heap)
            self._heap.clear()
            return n


# module-level scheduler singleton
inference_scheduler = InferenceScheduler()
