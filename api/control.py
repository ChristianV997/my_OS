from fastapi import APIRouter
from fastapi import HTTPException

router = APIRouter()

STATE = {
    "paused_products": set(),
    "manual_budgets": {},
    "approved_products": set(),
}


@router.post("/pause/{product_id}")
def pause(product_id: str):
    STATE["paused_products"].add(product_id)
    return {"status": "paused"}


@router.post("/resume/{product_id}")
def resume(product_id: str):
    STATE["paused_products"].discard(product_id)
    return {"status": "resumed"}


@router.post("/budget/{product_id}")
def override_budget(product_id: str, budget: float):
    if budget <= 0:
        raise HTTPException(status_code=400, detail="budget must be positive")
    STATE["manual_budgets"][product_id] = budget
    return {"status": "updated"}


@router.post("/approve/{product_id}")
def approve(product_id: str):
    STATE["approved_products"].add(product_id)
    return {"status": "approved"}
