"""QuantizationConfig — hardware-aware model loading configurations.

Used by AirLLM and future local providers to select quantization mode
based on available VRAM and memory.

Modes:
  none    — float32/float16, fastest, highest quality, most VRAM
  4bit    — 4-bit NF4, 4–8 GB VRAM, recommended for laptops
  8bit    — 8-bit int, 8–12 GB VRAM, better quality than 4bit
  gguf    — CPU-optimised llama.cpp format, no VRAM required
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

QuantizationMode = Literal["none", "4bit", "8bit", "gguf"]


@dataclass
class QuantizationConfig:
    mode:                    QuantizationMode = "4bit"
    device_map:              str              = "auto"
    max_gpu_memory_gb:       float            = 4.0
    max_cpu_memory_gb:       float            = 32.0
    compute_dtype:           str              = "float16"

    # BitsAndBytes (4bit / 8bit)
    load_in_4bit:            bool  = False
    load_in_8bit:            bool  = False
    bnb_4bit_compute_dtype:  str   = "float16"
    bnb_4bit_quant_type:     str   = "nf4"
    bnb_4bit_use_double_quant: bool = True

    def to_transformers_kwargs(self) -> dict:
        """Convert to kwargs accepted by transformers.AutoModelForCausalLM.from_pretrained()."""
        if self.mode == "none":
            return {"device_map": self.device_map, "torch_dtype": "auto"}
        if self.mode == "8bit":
            return {"device_map": self.device_map, "load_in_8bit": True}
        if self.mode == "4bit":
            try:
                from transformers import BitsAndBytesConfig
                bnb_cfg = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=self.bnb_4bit_compute_dtype,
                    bnb_4bit_quant_type=self.bnb_4bit_quant_type,
                    bnb_4bit_use_double_quant=self.bnb_4bit_use_double_quant,
                )
                return {"device_map": self.device_map, "quantization_config": bnb_cfg}
            except ImportError:
                return {"device_map": self.device_map, "load_in_4bit": True}
        return {"device_map": self.device_map}


# ── preset configurations ─────────────────────────────────────────────────────

CONFIGS: dict[str, QuantizationConfig] = {
    "none": QuantizationConfig(mode="none", load_in_4bit=False, load_in_8bit=False),

    "4bit": QuantizationConfig(
        mode="4bit",
        load_in_4bit=True,
        max_gpu_memory_gb=4.0,
        max_cpu_memory_gb=32.0,
    ),

    "8bit": QuantizationConfig(
        mode="8bit",
        load_in_8bit=True,
        max_gpu_memory_gb=8.0,
        max_cpu_memory_gb=32.0,
    ),

    "gguf": QuantizationConfig(
        mode="gguf",
        device_map="cpu",
        max_gpu_memory_gb=0.0,
        max_cpu_memory_gb=32.0,
        compute_dtype="float32",
    ),

    # AirLLM presets
    "airllm_4bit": QuantizationConfig(
        mode="4bit",
        load_in_4bit=True,
        max_gpu_memory_gb=4.0,
        max_cpu_memory_gb=32.0,
    ),
    "airllm_8bit": QuantizationConfig(
        mode="8bit",
        load_in_8bit=True,
        max_gpu_memory_gb=8.0,
        max_cpu_memory_gb=32.0,
    ),
}


def get_config(mode: str | None = None) -> QuantizationConfig:
    """Return a QuantizationConfig for the given mode string.

    Falls back to AIRLLM_COMPRESSION env var, then "4bit".
    """
    if mode is None:
        mode = os.getenv("AIRLLM_COMPRESSION", "4bit")
    return CONFIGS.get(mode, CONFIGS["4bit"])


def detect_best_config() -> QuantizationConfig:
    """Auto-select quantization based on available VRAM.

    Requires torch.  Returns "none" if torch is not available.
    """
    try:
        import torch
        if not torch.cuda.is_available():
            return CONFIGS["gguf"]  # CPU only
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        if vram_gb >= 16:
            return CONFIGS["none"]
        if vram_gb >= 8:
            return CONFIGS["8bit"]
        return CONFIGS["4bit"]
    except Exception:
        return CONFIGS["4bit"]  # safe default
