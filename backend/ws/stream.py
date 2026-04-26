"""backend.ws.stream — reconnect-safe WebSocket stream.

Features
--------
- **Replay on reconnect**: new clients receive the last N events from the
  broker's in-process replay buffer before the live stream starts.
- **Heartbeat**: a ``{"type": "heartbeat", "ts": <float>}`` frame is sent
  every ``heartbeat_s`` seconds so the client's TCP connection doesn't time
  out during quiet periods.
- **Throttle**: a configurable minimum interval between consume() calls
  prevents tight-looping when the stream is idle.
- **Error isolation**: a WebSocket error or disconnect closes only that
  connection; the broker and replay buffer are unaffected.

Wire format
-----------
Events are sent as JSON strings (``ws.send_text(...)``).  The payload is
the raw event dict — identical to what the previous ``api/ws.py`` sent —
so existing frontend code needs no changes.

Heartbeat frames have ``type="heartbeat"``; the frontend ignores unknown
types gracefully (``handleEvent`` in ``useMetrics.ts`` has no fallthrough).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

_log = logging.getLogger(__name__)

_HEARTBEAT_S    = 30.0    # seconds between heartbeat frames
_IDLE_SLEEP_S   = 0.1     # sleep when stream is empty
_REPLAY_N       = 30      # events to replay on reconnect


class WebSocketStream:
    """Manages a single WebSocket connection with replay + heartbeat."""

    def __init__(
        self,
        heartbeat_s: float = _HEARTBEAT_S,
        idle_sleep_s: float = _IDLE_SLEEP_S,
        replay_n: int = _REPLAY_N,
    ):
        self._heartbeat_s  = heartbeat_s
        self._idle_sleep_s = idle_sleep_s
        self._replay_n     = replay_n

    async def handle(self, ws: Any) -> None:
        """Accept a WebSocket connection and stream events until disconnect."""
        from backend.pubsub.broker import broker

        try:
            await ws.accept()
        except Exception:
            return

        # ── 1. Hydrate client with recent events ────────────────────────────
        # Prefer durable replay store (survives restarts) over in-process buffer.
        replay_payloads = self._load_replay_payloads(broker)
        for payload_json in replay_payloads:
            try:
                await ws.send_text(payload_json)
            except Exception:
                return   # client disconnected during replay

        # ── 2. Stream live events ────────────────────────────────────────────
        last_hb = time.time()
        while True:
            try:
                # consume() is blocking (up to STREAM_READ_BLOCK_MS ms) — run in thread
                envelopes = await asyncio.to_thread(
                    broker.consume, "ws", "ws_consumer"
                )
            except Exception as exc:
                _log.warning("ws_consume_error error=%s", exc)
                await asyncio.sleep(self._idle_sleep_s)
                continue

            for env in envelopes:
                try:
                    await ws.send_text(env.payload_json())
                except Exception:
                    return   # client disconnected

            # heartbeat if no events were sent recently
            now = time.time()
            if now - last_hb >= self._heartbeat_s:
                try:
                    await ws.send_text(json.dumps({"type": "heartbeat", "ts": now}))
                    last_hb = now
                except Exception:
                    return

            if not envelopes:
                await asyncio.sleep(self._idle_sleep_s)

    def _load_replay_payloads(self, broker: Any) -> list[str]:
        """Return recent event payloads as JSON strings for WS hydration.

        Tries the durable RuntimeReplayStore first (survives process restarts).
        Falls back to the in-process ReplayBuffer if the store is unavailable.
        """
        try:
            from backend.runtime.replay_store import runtime_replay_store
            rows = runtime_replay_store.recent(n=self._replay_n)
            if rows:
                return [
                    json.dumps(r["payload"], default=str)
                    for r in rows
                    if r.get("payload")
                ]
        except Exception:
            pass
        # fallback: in-process buffer (lost on restart but always available)
        return [env.payload_json() for env in broker.replay.recent(n=self._replay_n)]


# ── module-level singleton ────────────────────────────────────────────────────

ws_stream = WebSocketStream()
