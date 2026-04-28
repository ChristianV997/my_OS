"""InferenceScheduler — concurrency control and batch dispatch.

Prevents thundering-herd on the inference router by enforcing a
configurable maximum number of concurrent inference calls.

Also provides submit_batch() for parallel embedding generation.

Environment variables:
  INFERENCE_MAX_CONCURRENT   Max simultaneous calls   (default: 4)
  INFERENCE_QUEUE_TIMEOUT_S  Per-call timeout seconds (default: 120)
"""
from __future__ import annotations

import concurrent.futures
import logging
import os
import threading
import time
from typing import Callable

from .models.inference_request  import InferenceRequest
from .models.inference_response import InferenceResponse
from .models.embedding_request  import EmbeddingRequest

_log = logging.getLogger(__name__)

_MAX_CONCURRENT   = int(os.getenv("INFERENCE_MAX_CONCURRENT",   "4"))
_QUEUE_TIMEOUT_S  = float(os.getenv("INFERENCE_QUEUE_TIMEOUT_S", "120"))


class InferenceScheduler:
    """Semaphore-based concurrency limiter for the inference router."""

    def __init__(
        self,
        max_concurrent: int   = _MAX_CONCURRENT,
        timeout_s:      float = _QUEUE_TIMEOUT_S,
    ) -> None:
        self._sem     = threading.Semaphore(max_concurrent)
        self._timeout = timeout_s
        self._inflight = 0
        self._lock     = threading.Lock()

    # ── single request ────────────────────────────────────────────────────────

    def submit(
        self,
        request: InferenceRequest,
        router,                       # InferenceRouter — avoid circular import
    ) -> InferenceResponse:
        acquired = self._sem.acquire(timeout=self._timeout)
        if not acquired:
            _log.warning(
                "inference_queue_timeout seq=%s timeout_s=%s",
                request.sequence_id, self._timeout,
            )
            raise TimeoutError(
                f"Inference queue full — could not acquire slot within {self._timeout}s"
            )
        with self._lock:
            self._inflight += 1
        try:
            return router.complete(request)
        finally:
            with self._lock:
                self._inflight -= 1
            self._sem.release()

    # ── batch requests ────────────────────────────────────────────────────────

    def submit_batch(
        self,
        requests: list[InferenceRequest],
        router,
        max_workers: int | None = None,
    ) -> list[InferenceResponse]:
        """Execute requests in parallel, honouring the concurrency limit."""
        workers = min(max_workers or _MAX_CONCURRENT, len(requests), _MAX_CONCURRENT)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(self.submit, req, router) for req in requests]
            results = []
            for f in concurrent.futures.as_completed(futures, timeout=self._timeout * 2):
                try:
                    results.append(f.result())
                except Exception as exc:
                    _log.error("batch_inference_failed error=%s", exc)
        return results

    # ── embedding batch ───────────────────────────────────────────────────────

    def submit_embed(
        self,
        request: EmbeddingRequest,
        router,
    ) -> list[list[float]]:
        acquired = self._sem.acquire(timeout=self._timeout)
        if not acquired:
            raise TimeoutError("Inference queue full for embedding request")
        try:
            return router.embed(request)
        finally:
            self._sem.release()

    # ── diagnostics ───────────────────────────────────────────────────────────

    @property
    def inflight(self) -> int:
        return self._inflight


# ── module-level singleton ────────────────────────────────────────────────────

_scheduler: InferenceScheduler | None = None
_sched_lock = threading.Lock()


def get_scheduler() -> InferenceScheduler:
    global _scheduler
    if _scheduler is None:
        with _sched_lock:
            if _scheduler is None:
                _scheduler = InferenceScheduler()
    return _scheduler
