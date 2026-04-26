"""api.ws — WebSocket live event stream endpoint.

Delegates to ``backend.ws.stream.ws_stream`` which provides:
  - replay-on-reconnect (last 30 events from the broker's replay buffer)
  - heartbeat frames every 30 s
  - typed EventEnvelope routing through the canonical broker

The ``event_stream`` function signature is kept identical so ``backend/api.py``
does not need to change its import.
"""
from fastapi import WebSocket

from backend.ws.stream import ws_stream


async def event_stream(ws: WebSocket) -> None:  # noqa: D401
    await ws_stream.handle(ws)
