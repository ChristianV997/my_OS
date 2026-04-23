class AdsAgent:
    """Launches, pauses, and resumes ad campaigns for pods."""

    def launch(self, pod) -> dict:
        """Launch a campaign for the given pod."""
        return {
            "pod_id": pod.id,
            "platform": pod.platform,
            "status": "launched",
            "budget": pod.budget,
            "creatives": pod.creatives,
        }

    def pause(self, pod_id: str) -> dict:
        return {"pod_id": pod_id, "status": "paused"}

    def resume(self, pod_id: str) -> dict:
        return {"pod_id": pod_id, "status": "resumed"}
