"""backend.inference.providers.vllm — vLLM inference provider.

Communicates with a vLLM OpenAI-compatible server.

Config (via environment variables)
-----------------------------------
VLLM_BASE_URL       — base URL of the vLLM server (default: http://localhost:8000)
VLLM_DEFAULT_MODEL  — default model (default: "default")
VLLM_TIMEOUT        — request timeout in seconds (default: 120)
VLLM_API_KEY        — optional API key if server requires auth
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

_BASE_URL      = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
_DEFAULT_MODEL = os.getenv("VLLM_DEFAULT_MODEL", "default")
_TIMEOUT       = int(os.getenv("VLLM_TIMEOUT", "120"))
_API_KEY       = os.getenv("VLLM_API_KEY", "")


class VLLMProvider(BaseProvider):
    """vLLM provider via OpenAI-compatible HTTP API."""

    name = "vllm"
    supports_streaming = True

    def _get_client(self):
        try:
            import openai  # noqa: PLC0415
            kwargs: dict = {"base_url": f"{_BASE_URL}/v1"}
            if _API_KEY:
                kwargs["api_key"] = _API_KEY
            else:
                kwargs["api_key"] = "not-needed"
            return openai.OpenAI(**kwargs)
        except Exception as exc:
            _log.warning("vllm_client_init_failed error=%s", exc)
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
                "vllm client init failed — openai SDK required",
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
            _log.warning("vllm_complete_failed error=%s", exc)
            return self._make_error_response(
                request, self.name, str(exc), start_time=start
            )

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        client = self._get_client()
        if client is None:
            yield "[vllm_stream_unavailable]"
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
            _log.warning("vllm_stream_failed error=%s", exc)
            yield f"[vllm_stream_error: {exc}]"

    def health_check(self) -> bool:
        try:
            import httpx  # noqa: PLC0415
            r = httpx.get(f"{_BASE_URL}/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False
