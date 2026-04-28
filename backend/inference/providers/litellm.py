"""backend.inference.providers.litellm — LiteLLM compatibility adapter.

LiteLLM provides a unified interface to 100+ LLM providers.  This adapter
wraps it to fit the BaseProvider contract.

Config (via environment variables)
-----------------------------------
LITELLM_DEFAULT_MODEL — default model string (default: "gpt-4o-mini")
Any provider-specific keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) are
picked up by litellm automatically.
"""
from __future__ import annotations

import logging
import os
import time
from typing import AsyncIterator

from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.inference_response import InferenceResponse, TokenUsage
from backend.inference.providers.base import BaseProvider

_log = logging.getLogger(__name__)

_DEFAULT_MODEL = os.getenv("LITELLM_DEFAULT_MODEL", "gpt-4o-mini")


class LiteLLMProvider(BaseProvider):
    """LiteLLM multi-provider adapter."""

    name = "litellm"
    supports_streaming = True
    supports_embeddings = True

    def _build_messages(self, request: InferenceRequest) -> list[dict]:
        if request.messages:
            return request.messages
        msgs = []
        if request.system_prompt:
            msgs.append({"role": "system", "content": request.system_prompt})
        msgs.append({"role": "user", "content": request.prompt})
        return msgs

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        start = time.time()
        try:
            import litellm  # type: ignore[import] # noqa: PLC0415
            model = request.model if request.model != "default" else _DEFAULT_MODEL
            kwargs: dict = {"model": model, "messages": self._build_messages(request)}
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens

            resp = litellm.completion(**kwargs)
            text = resp.choices[0].message.content or ""
            usage_obj = resp.usage
            usage = TokenUsage(
                prompt_tokens=getattr(usage_obj, "prompt_tokens", 0),
                completion_tokens=getattr(usage_obj, "completion_tokens", 0),
                total_tokens=getattr(usage_obj, "total_tokens", 0),
            )
            return self._make_response(
                request,
                text=text,
                provider=self.name,
                model=model,
                usage=usage,
                start_time=start,
            )
        except ImportError:
            return self._make_error_response(
                request, self.name,
                "litellm not installed — pip install litellm",
                start_time=start,
            )
        except Exception as exc:
            _log.warning("litellm_complete_failed error=%s", exc)
            return self._make_error_response(
                request, self.name, str(exc), start_time=start
            )

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        try:
            import litellm  # type: ignore[import] # noqa: PLC0415
            model = request.model if request.model != "default" else _DEFAULT_MODEL
            kwargs: dict = {
                "model": model,
                "messages": self._build_messages(request),
                "stream": True,
            }
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens

            for chunk in litellm.completion(**kwargs):
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except ImportError:
            yield "[litellm_not_installed]"
        except Exception as exc:
            _log.warning("litellm_stream_failed error=%s", exc)
            yield f"[litellm_stream_error: {exc}]"

    def embed(self, request):
        from backend.inference.models.embedding_request import EmbeddingRequest, EmbeddingResponse
        start = time.time()
        try:
            import litellm  # type: ignore[import] # noqa: PLC0415
            model = request.model if request.model != "default" else "text-embedding-3-small"
            resp = litellm.embedding(model=model, input=request.texts)
            embeddings = [item["embedding"] for item in resp.data]
            latency_ms = (time.time() - start) * 1000.0
            return EmbeddingResponse(
                request_id=request.request_id,
                model=model,
                provider=self.name,
                embeddings=embeddings,
                latency_ms=latency_ms,
                sequence_id=request.sequence_id,
                replay_hash=request.replay_hash,
            )
        except ImportError:
            return EmbeddingResponse(
                request_id=request.request_id,
                provider=self.name,
                model=request.model,
                sequence_id=request.sequence_id,
                replay_hash=request.replay_hash,
                error="litellm not installed",
            )
        except Exception as exc:
            _log.warning("litellm_embed_failed error=%s", exc)
            return EmbeddingResponse(
                request_id=request.request_id,
                provider=self.name,
                model=request.model,
                sequence_id=request.sequence_id,
                replay_hash=request.replay_hash,
                error=str(exc),
            )

    def health_check(self) -> bool:
        try:
            import litellm  # type: ignore[import] # noqa: F401
            return True
        except ImportError:
            return False
