from fastapi import APIRouter, Depends, HTTPException

from api.security import enforce_rate_limit, require_control_auth
from core.control_state import (
    get_control_snapshot,
    load_control_state,
    mutate_control_state,
    reset_control_state,
)

router = APIRouter()


@router.post("/pause/{product_id}")
def pause(
    product_id: str,
    _auth: None = Depends(require_control_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    mutate_control_state(lambda state: state["paused_products"].add(product_id))
    return {"status": "paused"}


@router.post("/resume/{product_id}")
def resume(
    product_id: str,
    _auth: None = Depends(require_control_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    mutate_control_state(lambda state: state["paused_products"].discard(product_id))
    return {"status": "resumed"}


@router.post("/budget/{product_id}")
def override_budget(
    product_id: str,
    budget: float,
    _auth: None = Depends(require_control_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    if budget <= 0:
        raise HTTPException(status_code=400, detail="budget must be positive")
    mutate_control_state(lambda state: state["manual_budgets"].__setitem__(product_id, float(budget)))
    return {"status": "updated"}


@router.post("/approve/{product_id}")
def approve(
    product_id: str,
    _auth: None = Depends(require_control_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    mutate_control_state(lambda state: state["approved_products"].add(product_id))
    return {"status": "approved"}


@router.get("/state")
def state_snapshot(
    _auth: None = Depends(require_control_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    return get_control_snapshot()


def is_product_approved(product_id: str) -> bool:
    state = load_control_state()
    return product_id in state["approved_products"]


__all__ = [
    "approve",
    "override_budget",
    "pause",
    "resume",
    "get_control_snapshot",
    "reset_control_state",
    "is_product_approved",
]
