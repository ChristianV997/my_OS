from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

from api.control import router as control_router
from api.dashboard import router as dashboard_router
from api.pods import router as pods_router
from api.ws import event_stream
from core.bridge import Bridge
from tasks.discovery import run_discovery

app = FastAPI(title="UPOS Execution API")
bridge = Bridge()

_RUNTIME_STATE = {
    "paused": False,
    "last_cycle": None,
    "cycles": 0,
}


class IntelligenceRequest(BaseModel):
    keywords: list[str]


@app.get("/status")
def status():
    return {
        "service": "upos",
        "status": "ok",
        "runtime": _RUNTIME_STATE,
    }


@app.post("/run-intelligence")
def run_intelligence_endpoint(payload: IntelligenceRequest):
    launched = bridge.execute(payload.keywords)
    return {"launched": launched}


@app.post("/run-discovery")
def run_discovery_endpoint():
    launched = run_discovery.delay()
    return {"status": "queued", "result": launched}


@app.post("/cycle")
def cycle_endpoint():
    _RUNTIME_STATE["cycles"] += 1
    _RUNTIME_STATE["last_cycle"] = _RUNTIME_STATE["cycles"]
    return {
        "status": "ok",
        "cycle": _RUNTIME_STATE["cycles"],
        "paused": _RUNTIME_STATE["paused"],
    }


@app.post("/runner/pause")
def pause_runner_endpoint():
    _RUNTIME_STATE["paused"] = True
    return {"status": "paused", "runtime": _RUNTIME_STATE}


@app.post("/runner/resume")
def resume_runner_endpoint():
    _RUNTIME_STATE["paused"] = False
    return {"status": "resumed", "runtime": _RUNTIME_STATE}


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await event_stream(ws)


app.include_router(control_router, prefix="/control")
app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(pods_router)
