class EmbeddingEngine:
    def __init__(self):
        self._rows = []

    def add(self, text, metadata):
        tokens = set((text or "").lower().split())
        self._rows.append({"tokens": tokens, "text": text, "metadata": metadata})

    def search(self, query, top_k=5):
        query_tokens = set((query or "").lower().split())

        scored = []
        for row in self._rows:
            overlap = len(query_tokens & row["tokens"])
            scored.append((overlap, row["metadata"]))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [metadata for score, metadata in scored if score > 0][:top_k]
