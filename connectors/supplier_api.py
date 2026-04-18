class SupplierAPI:
    def search(self, keyword):
        return [{
            "name": keyword,
            "cost": 8,
            "shipping_days": 7,
            "rating": 4.7,
        }]
