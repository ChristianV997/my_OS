class SupplierAPI:
    """Stub supplier connector for local validation and tests."""

    def search(self, keyword):
        return [{
            "name": keyword,
            "cost": 8,
            "shipping_days": 7,
            "rating": 4.7,
        }]
