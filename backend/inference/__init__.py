"""backend.inference — centralized inference kernel for my_OS.

All model calls (local and cloud) route through router.py.
Supports deterministic replay, telemetry, streaming, and fallback scheduling.
"""
