import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request, WebSocket

_RATE_LOCK = threading.Lock()
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def _expected_key(scope: str) -> str:
    if scope == "control":
        return os.getenv("UPOS_CONTROL_API_KEY", os.getenv("UPOS_API_KEY", "")).strip()
    if scope == "execution":
        return os.getenv("UPOS_EXEC_API_KEY", os.getenv("UPOS_API_KEY", "")).strip()
    return os.getenv("UPOS_API_KEY", "").strip()


def _extract_key(raw: str | None) -> str:
    if not raw:
        return ""
    value = raw.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value


def _validate_scope_key(scope: str, auth_header: str | None, x_api_key: str | None) -> None:
    expected = _expected_key(scope)
    if not expected:
        return
    candidate = _extract_key(auth_header) or (x_api_key or "").strip()
    if candidate != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


def require_control_auth(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    _validate_scope_key("control", authorization, x_api_key)


def require_execution_auth(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    _validate_scope_key("execution", authorization, x_api_key)


def enforce_rate_limit(request: Request) -> None:
    limit = max(1, int(os.getenv("UPOS_RATE_LIMIT_REQUESTS", "60")))
    window_sec = max(1, int(os.getenv("UPOS_RATE_LIMIT_WINDOW_SEC", "60")))
    client = request.client.host if request.client else ""
    trust_proxy = os.getenv("UPOS_TRUST_PROXY_HEADERS", "0") == "1"
    if not client and trust_proxy:
        client = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if not client:
        raise HTTPException(status_code=400, detail="client_identification_required")
    key = f"{client}:{request.url.path}"
    now = time.monotonic()
    threshold = now - window_sec

    with _RATE_LOCK:
        bucket = _RATE_BUCKETS[key]
        while bucket and bucket[0] < threshold:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="rate_limit_exceeded")
        bucket.append(now)


async def authorize_websocket(ws: WebSocket, scope: str = "execution") -> None:
    expected = _expected_key(scope)
    if not expected:
        return
    auth_header = ws.headers.get("authorization")
    x_api_key = ws.headers.get("x-api-key") or ws.query_params.get("api_key")
    candidate = _extract_key(auth_header) or (x_api_key or "").strip()
    if candidate != expected:
        await ws.close(code=1008)
        raise RuntimeError("unauthorized websocket")
