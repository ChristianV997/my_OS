import logging
import os
import time
import uuid
from datetime import datetime, timezone

import duckdb
from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.control import router as control_router
from api.dashboard import router as dashboard_router
from api.security import enforce_rate_limit, require_execution_auth
from api.task_response import serialize_task_launch
from api.ws import event_stream
from backend.core.serializer import STATE_PATH as BACKEND_STATE_PATH
from core.stream import dependency_status
from tasks.discovery import run_discovery, run_intelligence_pipeline

app = FastAPI(title="UPOS Execution API")
logger = logging.getLogger(__name__)


class IntelligenceRequest(BaseModel):
    keywords: list[str]


def _check_db_dependency() -> dict:
    path = os.getenv("UPOS_STATE_DB_PATH", BACKEND_STATE_PATH)
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        con = duckdb.connect(path)
        con.execute("SELECT 1")
        con.close()
        return {"ok": True, "path": path}
    except Exception as exc:
        return {"ok": False, "path": path, "error_category": type(exc).__name__}


def _error_category(status_code: int) -> str:
    if status_code == 401:
        return "auth_error"
    if status_code == 429:
        return "rate_limit"
    if 400 <= status_code < 500:
        return "client_error"
    return "server_error"


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.error(
            "request_failed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "category": "server_error",
                "error_type": "internal_error",
                "duration_ms": elapsed_ms,
            },
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "category": "server_error", "request_id": request_id},
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    category = _error_category(response.status_code)
    logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "category": category,
            "duration_ms": elapsed_ms,
        },
    )
    response.headers["x-request-id"] = request_id
    return response


@app.get("/status")
def status():
    return {
        "service": "upos",
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    db = _check_db_dependency()
    stream = dependency_status()
    queue = {"ok": hasattr(run_discovery, "delay"), "task": "run_discovery"}
    checks = {"db": db, "stream": stream, "queue": queue}
    ready = bool(db.get("ok")) and bool(queue.get("ok"))
    status_code = 200 if ready else 503
    payload = {"status": "ready" if ready else "degraded", "checks": checks}
    return JSONResponse(status_code=status_code, content=payload)


@app.post("/run-intelligence")
def run_intelligence_endpoint(
    payload: IntelligenceRequest,
    _auth: None = Depends(require_execution_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    launched = run_intelligence_pipeline.delay(payload.keywords)
    return serialize_task_launch("run_intelligence", launched)


@app.post("/run-discovery")
def run_discovery_endpoint(
    _auth: None = Depends(require_execution_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    launched = run_discovery.delay()
    return serialize_task_launch("run_discovery", launched)


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await event_stream(ws)


app.include_router(control_router, prefix="/control")
app.include_router(dashboard_router, prefix="/dashboard")
