import requests


class ShopifyScraper:
    def fetch_products(self, store_url):
        url = f"{store_url.rstrip('/')}/products.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()

        products = []

        for product in payload.get("products", []):
            variants = product.get("variants") or [{}]
            price = float(variants[0].get("price", 0))

            products.append({
                "title": product.get("title", ""),
                "price": price,
            })

        return products
