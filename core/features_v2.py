import numpy as np

from core.embeddings import EmbeddingEngine

_engine = EmbeddingEngine()

_EMBEDDING_DIM = 16
_NUMERIC_DIM = 6
FEATURE_DIM = _EMBEDDING_DIM + _NUMERIC_DIM


def _product_embedding(signal):
    title = signal.get("title", signal.get("product", ""))
    category = signal.get("category", "")
    text = f"{title} {category}".strip()

    _engine.add(text, signal)

    tokens = set(text.lower().split())
    vec = np.zeros(_EMBEDDING_DIM)
    for i, tok in enumerate(list(tokens)[:_EMBEDDING_DIM]):
        vec[i] = hash(tok) % 100 / 100.0
    return vec


def build_features(signal, metrics, tribe=None):
    raw_emb = _product_embedding(signal)
    if len(raw_emb) < _EMBEDDING_DIM:
        emb = np.pad(raw_emb, (0, _EMBEDDING_DIM - len(raw_emb)))
    else:
        emb = raw_emb[:_EMBEDDING_DIM]

    numeric = np.array([
        float(signal.get("estimated_margin", 0)),
        float(signal.get("competition", 0)),
        float(metrics.get("ctr", 0)),
        float(metrics.get("cpc", 0)),
        float(metrics.get("spend", 0)),
        float(metrics.get("revenue", 0)),
    ])

    return np.concatenate([emb, numeric])
