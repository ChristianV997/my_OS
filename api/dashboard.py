from fastapi import APIRouter

from backend.core.state import SystemState

router = APIRouter()
_state = SystemState()


@router.get("/product/{product_id}")
def product_lifecycle(product_id: str):
    events = [row for row in _state.event_log.rows if row.get("product_id") == product_id]

    return [
        {
            "timestamp": event.get("timestamp"),
            "roas": event.get("roas", 0),
            "spend": event.get("cost", event.get("spend", 0)),
            "revenue": event.get("revenue", 0),
        }
        for event in events
    ]
