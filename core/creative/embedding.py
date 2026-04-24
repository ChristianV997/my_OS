import numpy as np


def embed_creative(script: str) -> np.ndarray:
    """Return a numeric embedding for *script*.

    This is a placeholder that returns a random 128-dim vector. Replace with
    a real model (e.g. HuggingFace sentence-transformers or OpenAI embeddings)
    in production.
    """
    rng = np.random.default_rng(abs(hash(script)) % (2**31))
    return rng.random(128).astype(np.float32)
