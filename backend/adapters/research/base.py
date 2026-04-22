from abc import ABC, abstractmethod
from typing import Any


class ResearchSourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        raise NotImplementedError
