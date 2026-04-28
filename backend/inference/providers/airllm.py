"""AirLLMProvider — large local models on low-VRAM hardware via AirLLM.

AirLLM streams model layers from disk, enabling 70B+ parameter models on
systems with 4–8 GB VRAM.  It is the preferred provider when running on
a laptop without a datacenter GPU.

Environment variables:
  AIRLLM_MODEL        HuggingFace model ID or local path  (default: meta-llama/Llama-3.2-1B)
  AIRLLM_COMPRESSION  "4bit" | "8bit" | "none"            (default: 4bit)
  AIRLLM_CACHE_DIR    Disk cache directory                 (default: ~/.cache/airllm)
  AIRLLM_MAX_TOKENS   Hard cap on generation length        (default: 512)

Install (not in base requirements — optional):
  pip install airllm
"""
from __future__ import annotations

import logging
import os
import time
from typing import Generator

from .._utils import compute_replay_hash, now_ms
from ..models.embedding_request import EmbeddingRequest
from ..models.inference_request import InferenceRequest
from ..models.inference_response import InferenceResponse
from .base import BaseProvider

_log = logging.getLogger(__name__)

_MODEL_ID    = os.getenv("AIRLLM_MODEL",       "meta-llama/Llama-3.2-1B")
_COMPRESSION = os.getenv("AIRLLM_COMPRESSION", "4bit")
_CACHE_DIR   = os.getenv("AIRLLM_CACHE_DIR",   os.path.expanduser("~/.cache/airllm"))
_MAX_TOKENS  = int(os.getenv("AIRLLM_MAX_TOKENS", "512"))


class AirLLMProvider(BaseProvider):
    """Layered disk-streaming inference — low VRAM, large model support."""

    name = "airllm"

    def __init__(self) -> None:
        self._model     = None   # lazy-loaded on first complete() call
        self._tokenizer = None

    # ── availability ─────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        try:
            import airllm  # noqa: F401
            return True
        except ImportError:
            return False

    # ── model loading (lazy + cached) ─────────────────────────────────────────

    def _load(self):
        if self._model is not None:
            return self._model, self._tokenizer

        _log.info("airllm_loading model=%s compression=%s", _MODEL_ID, _COMPRESSION)
        try:
            from airllm import AutoModel  # noqa: PLC0415

            kwargs: dict = {"cache_dir": _CACHE_DIR}
            if _COMPRESSION in ("4bit", "8bit"):
                kwargs["compression"] = _COMPRESSION

            self._model = AutoModel.from_pretrained(_MODEL_ID, **kwargs)

            # AirLLM bundles the tokenizer; expose it for prompt encoding
            self._tokenizer = getattr(self._model, "tokenizer", None)
            if self._tokenizer is None:
                from transformers import AutoTokenizer  # noqa: PLC0415
                self._tokenizer = AutoTokenizer.from_pretrained(_MODEL_ID)

            _log.info("airllm_loaded model=%s", _MODEL_ID)
        except Exception as exc:
            _log.error("airllm_load_failed model=%s error=%s", _MODEL_ID, exc)
            raise

        return self._model, self._tokenizer

    # ── inference ─────────────────────────────────────────────────────────────

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        model, tokenizer = self._load()

        prompt = request.prompt
        if request.system:
            prompt = f"{request.system}\n\n{prompt}"

        # Deterministic generation when seed is set
        gen_kwargs: dict = {
            "max_new_tokens": min(request.max_tokens, _MAX_TOKENS),
            "temperature":    request.temperature,
            "do_sample":      request.temperature > 0,
        }
        if request.seed is not None:
            import torch
            torch.manual_seed(request.seed)

        t0 = now_ms()
        try:
            input_ids = tokenizer(prompt, return_tensors="pt").input_ids
            output    = model.generate(input_ids, **gen_kwargs)
            # Decode only the newly generated tokens
            new_ids = output[0][input_ids.shape[-1]:]
            content = tokenizer.decode(new_ids, skip_special_tokens=True)
        except Exception as exc:
            _log.error("airllm_generate_failed model=%s error=%s", _MODEL_ID, exc)
            raise

        latency = now_ms() - t0
        return InferenceResponse(
            content=content,
            provider="airllm",
            model=_MODEL_ID,
            sequence_id=request.sequence_id,
            replay_hash=compute_replay_hash(request),
            latency_ms=latency,
            prompt_tokens=input_ids.shape[-1],
            completion_tokens=len(new_ids),
        )

    # ── embeddings ────────────────────────────────────────────────────────────

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        """AirLLM does not expose an embedding API — raise to trigger fallback."""
        raise NotImplementedError(
            "AirLLMProvider does not support embeddings.  "
            "Use OpenAI or Ollama provider for embedding workloads."
        )

    # ── streaming ─────────────────────────────────────────────────────────────

    def stream(
        self, request: InferenceRequest
    ) -> Generator[str, None, InferenceResponse]:
        """AirLLM generates synchronously; yield the complete response as one chunk."""
        response = self.complete(request)
        yield response.content
        return response
