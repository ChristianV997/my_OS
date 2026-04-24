import numpy as np


class CreativeMemory:
    """Vector store for ad creatives — stores embeddings + metadata for
    similarity-based retrieval of past winners."""

    def __init__(self):
        self.vectors: list[np.ndarray] = []
        self.metadata: list[dict] = []

    def add(self, embedding: np.ndarray, meta: dict) -> None:
        self.vectors.append(embedding)
        self.metadata.append(meta)

    def similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    def query(self, embedding: np.ndarray, top_k: int = 3) -> list[dict]:
        if not self.vectors:
            return []

        sims = [
            (i, self.similarity(embedding, v))
            for i, v in enumerate(self.vectors)
        ]
        sims.sort(key=lambda x: x[1], reverse=True)
        return [self.metadata[i] for i, _ in sims[:top_k]]
