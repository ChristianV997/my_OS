import hashlib
import numpy as np


def embed_creative(script: str) -> np.ndarray:
    """Return a numeric embedding for *script*.

    This is a placeholder that returns a deterministic 128-dim vector derived
    from a SHA-256 hash of the script. Replace with a real model (e.g.
    HuggingFace sentence-transformers or OpenAI embeddings) in production.
    """
    digest = hashlib.sha256(script.encode()).digest()
    seed = int.from_bytes(digest[:4], "big")
    rng = np.random.default_rng(seed)
    return rng.random(128).astype(np.float32)
