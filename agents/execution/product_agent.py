class ProductAgent:
    """Selects and validates product opportunities from scored signals."""

    def select(self, signals: list) -> list:
        """Convert scored signals into product dicts."""
        products = []
        for signal in signals:
            products.append(
                {
                    "name": signal.get("product", "unknown"),
                    "score": signal.get("score", 0.0),
                    "source": signal.get("source", "unknown"),
                    "market": signal.get("market", "global"),
                    "platform": signal.get("platform", "meta"),
                }
            )
        return products

    def validate(self, product: dict) -> bool:
        """Return True if product has a name and a positive score."""
        return bool(product.get("name")) and product.get("score", 0) > 0
