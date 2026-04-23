import asyncio
import os

from fastapi import WebSocket, WebSocketDisconnect

from api.security import authorize_websocket
from core.stream import consume

WS_POLL_SLEEP_SECONDS = max(float(os.getenv("UPOS_WS_POLL_SLEEP_SEC", "0.2")), 0.01)
WS_CONSUME_TIMEOUT_SECONDS = max(float(os.getenv("UPOS_WS_CONSUME_TIMEOUT_SEC", "3")), 0.1)
WS_MAX_MESSAGES_PER_TICK = max(int(os.getenv("UPOS_WS_MAX_MESSAGES_PER_TICK", "100")), 1)
WS_MAX_EMPTY_POLLS = max(int(os.getenv("UPOS_WS_MAX_EMPTY_POLLS", "300")), 1)
WS_BACKPRESSURE_PAUSE_SECONDS = max(float(os.getenv("UPOS_WS_BACKPRESSURE_PAUSE_SEC", "0.05")), 0.0)


async def event_stream(ws: WebSocket):
    await authorize_websocket(ws, scope="execution")
    await ws.accept()
    empty_polls = 0

    while True:
        try:
            events = await asyncio.wait_for(asyncio.to_thread(consume), timeout=WS_CONSUME_TIMEOUT_SECONDS)
        except TimeoutError:
            empty_polls += 1
            if empty_polls >= WS_MAX_EMPTY_POLLS:
                await ws.close(code=1000)
                break
            await asyncio.sleep(WS_POLL_SLEEP_SECONDS)
            continue
        except WebSocketDisconnect:
            break
        except RuntimeError:
            break

        if not events:
            empty_polls += 1
            if empty_polls >= WS_MAX_EMPTY_POLLS:
                await ws.close(code=1000)
                break
            await asyncio.sleep(WS_POLL_SLEEP_SECONDS)
            continue

        empty_polls = 0
        sent = 0
        for _, messages in events:
            for _, payload in messages:
                data = payload.get("data")
                if not data:
                    continue
                await ws.send_text(data)
                sent += 1
                if sent >= WS_MAX_MESSAGES_PER_TICK:
                    await asyncio.sleep(WS_BACKPRESSURE_PAUSE_SECONDS)
                    break
            if sent >= WS_MAX_MESSAGES_PER_TICK:
                break
