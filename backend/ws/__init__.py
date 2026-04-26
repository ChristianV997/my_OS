"""backend.ws — reconnect-safe WebSocket stream for the MarketOS runtime.

Provides ``ws_stream``: the singleton WebSocketStream that wraps the broker
and serves all ``/ws`` connections with replay-on-reconnect + heartbeats.
"""
from backend.ws.stream import WebSocketStream, ws_stream

__all__ = ["WebSocketStream", "ws_stream"]
