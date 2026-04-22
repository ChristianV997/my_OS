import asyncio

from fastapi import WebSocket

from core.stream import consume


async def event_stream(ws: WebSocket):
    await ws.accept()

    while True:
        events = await asyncio.to_thread(consume)
        if not events:
            await asyncio.sleep(0.2)
            continue

        for _, messages in events:
            for _, payload in messages:
                await ws.send_text(payload["data"])
