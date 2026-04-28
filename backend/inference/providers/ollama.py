"""backend.inference.providers.ollama — Ollama local inference provider.

Communicates with a running Ollama server via its HTTP API.

Config (via environment variables)
-----------------------------------
OLLAMA_BASE_URL     — base URL of the Ollama server (default: http://localhost:11434)
OLLAMA_DEFAULT_MODEL — default model (default: "llama3")
OLLAMA_TIMEOUT      — request timeout in seconds (default: 120)
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import AsyncIterator

from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.inference_response import InferenceResponse, TokenUsage
from backend.inference.providers.base import BaseProvider

_log = logging.getLogger(__name__)

_BASE_URL     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3")
_TIMEOUT      = int(os.getenv("OLLAMA_TIMEOUT", "120"))


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider."""

    name = "ollama"
    supports_streaming = True
    supports_embeddings = True

    def _post_generate(self, payload: dict) -> dict:
        import httpx  # noqa: PLC0415
        url = f"{_BASE_URL}/api/generate"
        resp = httpx.post(url, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _build_prompt(self, request: InferenceRequest) -> str:
        if request.system_prompt:
            return f"{request.system_prompt}\n\n{request.prompt}"
        return request.prompt

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        start = time.time()
        try:
            model = request.model if request.model != "default" else _DEFAULT_MODEL
            payload: dict = {
                "model": model,
                "prompt": self._build_prompt(request),
                "stream": False,
                "options": {},
            }
            if request.temperature is not None:
                payload["options"]["temperature"] = request.temperature
            if request.max_tokens is not None:
                payload["options"]["num_predict"] = request.max_tokens

            data = self._post_generate(payload)
            text = data.get("response", "")
            usage = TokenUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            )
            return self._make_response(
                request,
                text=text,
                provider=self.name,
                model=data.get("model", model),
                usage=usage,
                start_time=start,
            )
        except Exception as exc:
            _log.warning("ollama_complete_failed error=%s", exc)
            return self._make_error_response(
                request, self.name, str(exc), start_time=start
            )

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        try:
            import httpx  # noqa: PLC0415
            model = request.model if request.model != "default" else _DEFAULT_MODEL
            payload: dict = {
                "model": model,
                "prompt": self._build_prompt(request),
                "stream": True,
                "options": {},
            }
            if request.temperature is not None:
                payload["options"]["temperature"] = request.temperature
            if request.max_tokens is not None:
                payload["options"]["num_predict"] = request.max_tokens

            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream(
                    "POST", f"{_BASE_URL}/api/generate", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
        except Exception as exc:
            _log.warning("ollama_stream_failed error=%s", exc)
            yield f"[ollama_stream_error: {exc}]"

    def embed(self, request):
        from backend.inference.models.embedding_request import EmbeddingRequest, EmbeddingResponse
        start = time.time()
        try:
            import httpx  # noqa: PLC0415
            model = request.model if request.model != "default" else _DEFAULT_MODEL
            embeddings = []
            for text in request.texts:
                payload = {"model": model, "prompt": text}
                resp = httpx.post(
                    f"{_BASE_URL}/api/embeddings",
                    json=payload,
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                embeddings.append(resp.json().get("embedding", []))
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
            _log.warning("ollama_embed_failed error=%s", exc)
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
            import httpx  # noqa: PLC0415
            r = httpx.get(f"{_BASE_URL}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False
