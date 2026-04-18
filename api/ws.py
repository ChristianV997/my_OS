from fastapi import WebSocket

from core.stream import consume


async def event_stream(ws: WebSocket):
    await ws.accept()

    while True:
        events = consume()

        for _, messages in events:
            for _, payload in messages:
                await ws.send_text(payload["data"])
