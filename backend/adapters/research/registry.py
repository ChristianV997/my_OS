from backend.adapters.research.base import ResearchSourceAdapter


class ResearchAdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, ResearchSourceAdapter] = {}

    def register(self, name: str, adapter: ResearchSourceAdapter) -> None:
        self._adapters[name] = adapter

    def get(self, name: str) -> ResearchSourceAdapter:
        if name not in self._adapters:
            raise KeyError(f"Unknown research adapter: {name}")
        return self._adapters[name]

    def all(self) -> dict[str, ResearchSourceAdapter]:
        return dict(self._adapters)
