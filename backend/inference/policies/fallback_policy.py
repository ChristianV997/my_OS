"""backend.inference.policies.fallback_policy — deterministic fallback scheduling.

Defines when and how the router falls back to the next provider in the chain.
Fallback is triggered when:
  - The primary provider returns an error response
  - A provider raises an exception

All fallback events MUST emit telemetry (handled in router.py / telemetry.py).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.inference.models.inference_response import InferenceResponse

_log = logging.getLogger(__name__)


class FallbackPolicy:
    """Decides whether a response warrants a fallback attempt.

    Parameters
    ----------
    max_retries : int
        Maximum number of fallback providers to try before giving up.
    retry_on_empty : bool
        If True, also fall back when the response text is empty.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_on_empty: bool = False,
    ) -> None:
        self.max_retries = max_retries
        self.retry_on_empty = retry_on_empty

    def should_fallback(
        self,
        response: "InferenceResponse",
        attempt: int,
    ) -> bool:
        """Return True if the router should try the next provider in the chain.

        Parameters
        ----------
        response : InferenceResponse
            The response from the most recent attempt.
        attempt : int
            0-indexed attempt number (0 = first try).
        """
        if attempt >= self.max_retries:
            _log.debug(
                "fallback_policy max_retries_reached attempt=%d max=%d",
                attempt,
                self.max_retries,
            )
            return False

        if response.error is not None:
            _log.debug(
                "fallback_policy triggered provider=%s error=%s",
                response.provider,
                response.error,
            )
            return True

        if self.retry_on_empty and not response.text.strip():
            _log.debug(
                "fallback_policy triggered on empty response provider=%s",
                response.provider,
            )
            return True

        return False
