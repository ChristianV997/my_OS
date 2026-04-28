"""backend.inference.providers.openai — OpenAI inference provider.

Uses the ``openai`` Python SDK (v1+).  Falls back gracefully if the SDK is not
installed or if OPENAI_API_KEY is absent — returns an error response instead of
raising so the fallback chain in the router can take over.

Config (via environment variables)
-----------------------------------
OPENAI_API_KEY      — required for real calls
OPENAI_BASE_URL     — optional; override for Azure / proxy endpoints
OPENAI_DEFAULT_MODEL — default model (default: "gpt-4o-mini")
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

_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")


class OpenAIProvider(BaseProvider):
    """OpenAI completion provider (chat completions API)."""

    name = "openai"
    supports_streaming = True
    supports_embeddings = True

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import openai  # noqa: PLC0415
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            kwargs: dict = {}
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
            self._client = openai.OpenAI(**kwargs)
            return self._client
        except Exception as exc:
            _log.warning("openai_client_init_failed error=%s", exc)
            return None

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
        client = self._get_client()
        if client is None:
            return self._make_error_response(
                request, self.name,
                "openai SDK not available or OPENAI_API_KEY missing",
                start_time=start,
            )

        try:
            model = request.model if request.model != "default" else _DEFAULT_MODEL
            kwargs: dict = {
                "model": model,
                "messages": self._build_messages(request),
            }
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens

            resp = client.chat.completions.create(**kwargs)
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
        except Exception as exc:
            _log.warning("openai_complete_failed error=%s", exc)
            return self._make_error_response(
                request, self.name, str(exc), start_time=start
            )

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        client = self._get_client()
        if client is None:
            yield "[openai_stream_unavailable]"
            return

        try:
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

            for chunk in client.chat.completions.create(**kwargs):
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as exc:
            _log.warning("openai_stream_failed error=%s", exc)
            yield f"[stream_error: {exc}]"

    def embed(self, request):
        from backend.inference.models.embedding_request import EmbeddingRequest, EmbeddingResponse
        start = time.time()
        client = self._get_client()
        if client is None:
            return EmbeddingResponse(
                request_id=request.request_id,
                provider=self.name,
                model=request.model,
                sequence_id=request.sequence_id,
                replay_hash=request.replay_hash,
                error="openai SDK not available or OPENAI_API_KEY missing",
            )
        try:
            model = request.model if request.model != "default" else "text-embedding-3-small"
            resp = client.embeddings.create(input=request.texts, model=model)
            embeddings = [item.embedding for item in resp.data]
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
        except Exception as exc:
            _log.warning("openai_embed_failed error=%s", exc)
            return EmbeddingResponse(
                request_id=request.request_id,
                provider=self.name,
                model=request.model,
                sequence_id=request.sequence_id,
                replay_hash=request.replay_hash,
                error=str(exc),
            )

    def health_check(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))
