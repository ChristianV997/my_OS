import json
import os
import threading
from typing import Any

CONTROL_STATE_PATH = os.getenv("UPOS_CONTROL_STATE_PATH", "state/control_state.json")

_LOCK = threading.RLock()
_DEFAULT_STATE = {
    "paused_products": [],
    "manual_budgets": {},
    "approved_products": [],
}


def _normalize(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    paused = raw.get("paused_products", [])
    approved = raw.get("approved_products", [])
    budgets = raw.get("manual_budgets", {})
    return {
        "paused_products": set(str(item) for item in paused),
        "approved_products": set(str(item) for item in approved),
        "manual_budgets": {str(k): float(v) for k, v in dict(budgets).items()},
    }


def _to_serializable(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "paused_products": sorted(state["paused_products"]),
        "approved_products": sorted(state["approved_products"]),
        "manual_budgets": dict(state["manual_budgets"]),
    }


def load_control_state() -> dict[str, Any]:
    with _LOCK:
        if not os.path.exists(CONTROL_STATE_PATH):
            return _normalize(_DEFAULT_STATE)
        try:
            with open(CONTROL_STATE_PATH, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            payload = _DEFAULT_STATE
        return _normalize(payload)


def save_control_state(state: dict[str, Any]) -> None:
    with _LOCK:
        directory = os.path.dirname(CONTROL_STATE_PATH)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = _to_serializable(_normalize(state))
        with open(CONTROL_STATE_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)


def mutate_control_state(mutator):
    with _LOCK:
        state = load_control_state()
        mutator(state)
        save_control_state(state)
        return state


def reset_control_state() -> dict[str, Any]:
    state = _normalize(_DEFAULT_STATE)
    save_control_state(state)
    return state


def get_control_snapshot() -> dict[str, Any]:
    return _to_serializable(load_control_state())


def is_approved(product_id: str) -> bool:
    state = load_control_state()
    return product_id in state["approved_products"]
