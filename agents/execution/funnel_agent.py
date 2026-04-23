class FunnelAgent:
    """Builds landing pages and conversion funnels for pods."""

    def build(self, pod) -> dict:
        """Generate a landing page configuration for the pod."""
        return {
            "pod_id": pod.id,
            "url": f"/funnel/{pod.id}",
            "product": pod.product,
            "headline": f"Get {pod.product} — Limited Time Offer",
            "platform": pod.platform,
        }
