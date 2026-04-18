from core.embeddings import EmbeddingEngine

embedder = EmbeddingEngine()


def update_learning(events):
    for event in events or []:
        hook = event.get("hook", "")
        angle = event.get("angle", "")
        text = f"{hook} {angle}".strip()
        embedder.add(text, event)

    return embedder.search("winning ads")
