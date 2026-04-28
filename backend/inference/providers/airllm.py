"""backend.inference.providers.airllm — AirLLM local inference provider.

AirLLM enables large-model inference on laptops with low VRAM by splitting
model layers and loading them on demand.

Features
--------
- Lazy loading: model is not loaded until the first completion call
- Deterministic generation config via request.replay_hash seeding
- Streaming compatibility: yields tokens progressively
- Telemetry instrumentation: timing and token counts surfaced via response

Config (via environment variables)
-----------------------------------
AIRLLM_MODEL_PATH    — path to the local model directory (required for real use)
AIRLLM_DEFAULT_MODEL — model identifier (default: "meta-llama/Llama-2-7b-chat-hf")
AIRLLM_MAX_LENGTH    — maximum generation tokens (default: 512)
AIRLLM_COMPRESSION   — compression level; "4bit" | "8bit" | None (default: "4bit")
AIRLLM_PREFILL_CHUNK — prefill chunk size for memory efficiency (default: 128)
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import AsyncIterator

from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.inference_response import InferenceResponse, TokenUsage
from backend.inference.providers.base import BaseProvider

_log = logging.getLogger(__name__)

_MODEL_PATH    = os.getenv("AIRLLM_MODEL_PATH", "")
_DEFAULT_MODEL = os.getenv("AIRLLM_DEFAULT_MODEL", "meta-llama/Llama-2-7b-chat-hf")
_MAX_LENGTH    = int(os.getenv("AIRLLM_MAX_LENGTH", "512"))
_COMPRESSION   = os.getenv("AIRLLM_COMPRESSION", "4bit") or None
_PREFILL_CHUNK = int(os.getenv("AIRLLM_PREFILL_CHUNK", "128"))


class AirLLMProvider(BaseProvider):
    """AirLLM provider for low-VRAM local inference.

    The model is loaded lazily on first use and cached for subsequent calls.
    """

    name = "airllm"
    supports_streaming = True

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._loaded_model_id: str | None = None

    # ── lazy loader ───────────────────────────────────────────────────────────

    def _ensure_loaded(self, model_id: str) -> bool:
        """Load model and tokenizer if not already loaded.  Returns True on success."""
        if self._model is not None and self._loaded_model_id == model_id:
            return True

        model_path = _MODEL_PATH or model_id

        try:
            from airllm import AutoModel  # type: ignore[import]
            kwargs: dict = {"prefill_chunk_size": _PREFILL_CHUNK}
            if _COMPRESSION:
                kwargs["compression"] = _COMPRESSION
            self._model = AutoModel.from_pretrained(model_path, **kwargs)
            self._loaded_model_id = model_id

            # Load the tokenizer separately for prompt encoding
            from transformers import AutoTokenizer  # type: ignore[import]
            self._tokenizer = AutoTokenizer.from_pretrained(model_path)
            _log.info("airllm_model_loaded model=%s", model_id)
            return True
        except ImportError:
            _log.warning(
                "airllm_import_failed — install airllm and transformers for local inference"
            )
            return False
        except Exception as exc:
            _log.warning("airllm_load_failed model=%s error=%s", model_id, exc)
            return False

    # ── deterministic generation seed ─────────────────────────────────────────

    @staticmethod
    def _seed_from_hash(replay_hash: str | None) -> int:
        """Derive a deterministic integer seed from the request replay_hash."""
        if not replay_hash:
            return 42
        return int(hashlib.sha256(replay_hash.encode()).hexdigest()[:8], 16)

    # ── completion ────────────────────────────────────────────────────────────

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        start = time.time()
        model_id = request.model if request.model not in ("default", "") else _DEFAULT_MODEL

        if not self._ensure_loaded(model_id):
            return self._make_error_response(
                request, self.name,
                "airllm model could not be loaded — check AIRLLM_MODEL_PATH and dependencies",
                start_time=start,
            )

        try:
            prompt = request.prompt
            if request.system_prompt:
                prompt = f"{request.system_prompt}\n\n{prompt}"

            seed = self._seed_from_hash(request.replay_hash)

            # Build generation kwargs deterministically
            gen_kwargs: dict = {
                "max_new_tokens": request.max_tokens or _MAX_LENGTH,
                "do_sample": True,
            }
            if request.temperature is not None:
                gen_kwargs["temperature"] = request.temperature
            else:
                gen_kwargs["temperature"] = 1.0

            # Set deterministic seed
            try:
                import torch  # type: ignore[import]
                torch.manual_seed(seed)
            except ImportError:
                pass

            # Tokenize
            inputs = self._tokenizer(prompt, return_tensors="pt")
            input_ids = inputs["input_ids"]
            prompt_len = input_ids.shape[-1]

            # Generate
            output_ids = self._model.generate(input_ids, **gen_kwargs)
            generated_ids = output_ids[0][prompt_len:]
            text = self._tokenizer.decode(generated_ids, skip_special_tokens=True)

            completion_tokens = len(generated_ids)
            usage = TokenUsage(
                prompt_tokens=prompt_len,
                completion_tokens=completion_tokens,
                total_tokens=prompt_len + completion_tokens,
            )
            return self._make_response(
                request,
                text=text,
                provider=self.name,
                model=model_id,
                usage=usage,
                start_time=start,
            )
        except Exception as exc:
            _log.warning("airllm_complete_failed error=%s", exc)
            return self._make_error_response(
                request, self.name, str(exc), start_time=start
            )

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        """Stream tokens from AirLLM generation.

        Runs the (synchronous) complete() call in a thread and yields the
        result as a single chunk.  True streaming requires the AirLLM
        TextIteratorStreamer integration which is added when available.
        """
        try:
            from transformers import TextIteratorStreamer  # type: ignore[import]
            import threading
            model_id = request.model if request.model not in ("default", "") else _DEFAULT_MODEL
            if not self._ensure_loaded(model_id):
                yield "[airllm_stream_unavailable]"
                return

            prompt = request.prompt
            if request.system_prompt:
                prompt = f"{request.system_prompt}\n\n{prompt}"

            seed = self._seed_from_hash(request.replay_hash)
            try:
                import torch  # type: ignore[import]
                torch.manual_seed(seed)
            except ImportError:
                pass

            inputs = self._tokenizer(prompt, return_tensors="pt")
            streamer = TextIteratorStreamer(
                self._tokenizer, skip_special_tokens=True
            )
            gen_kwargs: dict = {
                "input_ids": inputs["input_ids"],
                "max_new_tokens": request.max_tokens or _MAX_LENGTH,
                "streamer": streamer,
                "do_sample": True,
                "temperature": request.temperature if request.temperature is not None else 1.0,
            }

            thread = threading.Thread(target=self._model.generate, kwargs=gen_kwargs)
            thread.start()

            for token in streamer:
                yield token

            thread.join()

        except ImportError:
            # Fallback: run complete() synchronously
            resp = self.complete(request)
            yield resp.text

        except Exception as exc:
            _log.warning("airllm_stream_failed error=%s", exc)
            yield f"[airllm_stream_error: {exc}]"

    def health_check(self) -> bool:
        try:
            import airllm  # type: ignore[import] # noqa: F401
            return True
        except ImportError:
            return False
