import json
from typing import Any


def _safe_json_value(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def serialize_task_launch(task_name: str, task_result: Any) -> dict[str, Any]:
    task_id = getattr(task_result, "id", None) or getattr(task_result, "task_id", None)
    task_state = getattr(task_result, "state", None)
    if task_id:
        payload = {
            "status": "queued",
            "task": {
                "name": task_name,
                "id": str(task_id),
            },
        }
        if task_state is not None:
            payload["task"]["state"] = str(task_state)
        return payload
    return {
        "status": "completed",
        "task": {"name": task_name},
        "result": _safe_json_value(task_result),
    }
