class CreativeAgent:
    """Generates ad creatives for a pod."""

    def generate(self, pod) -> dict:
        """Generate a single creative asset for the given pod."""
        return {
            "pod_id": pod.id,
            "headline": f"Buy {pod.product} now!",
            "body": f"Best {pod.product} deals on {pod.platform}.",
            "cta": "Shop Now",
            "format": "image",
        }

    def batch_generate(self, pods: list, count: int = 3) -> dict:
        """Generate *count* creatives for each pod. Returns {pod_id: [creatives]}."""
        return {pod.id: [self.generate(pod) for _ in range(count)] for pod in pods}
