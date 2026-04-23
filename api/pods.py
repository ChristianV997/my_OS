from fastapi import APIRouter, HTTPException

from core.pods import pod_manager
from core.capital import capital_engine
from core.signals import signal_engine

router = APIRouter()


@router.get("/pods")
def list_pods():
    """List all pods with their current metrics and status."""
    return [p.to_dict() for p in pod_manager.list_all()]


@router.get("/pods/{pod_id}")
def get_pod(pod_id: str):
    """Return metrics and status for a specific pod."""
    pod = pod_manager.get(pod_id)
    if pod is None:
        raise HTTPException(status_code=404, detail="Pod not found")
    return pod.to_dict()


@router.get("/capital")
def capital_status():
    """Return budget allocation across active pods."""
    pods = pod_manager.list_all()
    return {
        "total_pods": len(pods),
        "active_pods": sum(1 for p in pods if p.status != "killed"),
        "allocation": capital_engine.allocate_budget(pods, 1000.0),
    }


@router.get("/signals")
def current_signals():
    """Return current scored product opportunities."""
    signals = signal_engine.get()
    return {"signals": signals, "count": len(signals)}
