"""backend.inference.quantization — quantization configuration helpers.

Provides utilities for configuring quantized model loading.  Used primarily
by the AirLLM provider and any future local-inference provider that needs
to load models with reduced precision to fit in available VRAM.

Quantization levels
--------------------
none   — full precision (FP32 / BF16 as loaded)
8bit   — INT8 quantization (bitsandbytes)
4bit   — INT4 quantization / GGUF (AirLLM / llama.cpp)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

QuantizationLevel = Literal["none", "8bit", "4bit"]


@dataclass
class QuantizationConfig:
    """Configuration for quantized model loading.

    Fields
    ------
    level           — quantization precision
    device          — target device ("cpu", "cuda", "mps")
    prefill_chunk   — token chunk size for memory-efficient prefill (AirLLM)
    offload_folder  — path for disk-offloaded weights (optional)
    """

    level: QuantizationLevel = "4bit"
    device: str = "cpu"
    prefill_chunk: int = 128
    offload_folder: str = ""

    def to_airllm_kwargs(self) -> dict:
        """Return kwargs suitable for AirLLM's AutoModel.from_pretrained."""
        kwargs: dict = {"prefill_chunk_size": self.prefill_chunk}
        if self.level in ("4bit", "8bit"):
            kwargs["compression"] = self.level
        if self.offload_folder:
            kwargs["offload_folder"] = self.offload_folder
        return kwargs

    def to_transformers_kwargs(self) -> dict:
        """Return kwargs suitable for HuggingFace AutoModel.from_pretrained."""
        kwargs: dict = {"device_map": "auto" if self.device != "cpu" else self.device}
        if self.level == "8bit":
            kwargs["load_in_8bit"] = True
        elif self.level == "4bit":
            kwargs["load_in_4bit"] = True
        return kwargs

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "device": self.device,
            "prefill_chunk": self.prefill_chunk,
            "offload_folder": self.offload_folder,
        }


def default_config(device: str = "cpu") -> QuantizationConfig:
    """Return a sensible default quantization config for the given device."""
    if device in ("cuda", "mps"):
        return QuantizationConfig(level="4bit", device=device)
    return QuantizationConfig(level="4bit", device="cpu")


def from_env() -> QuantizationConfig:
    """Build a QuantizationConfig from AIRLLM_* environment variables."""
    import os

    level_str = os.getenv("AIRLLM_COMPRESSION", "4bit") or "none"
    valid_levels: tuple[str, ...] = ("none", "8bit", "4bit")
    level: QuantizationLevel = level_str if level_str in valid_levels else "4bit"  # type: ignore[assignment]

    return QuantizationConfig(
        level=level,
        device=os.getenv("AIRLLM_DEVICE", "cpu"),
        prefill_chunk=int(os.getenv("AIRLLM_PREFILL_CHUNK", "128")),
        offload_folder=os.getenv("AIRLLM_OFFLOAD_FOLDER", ""),
    )
