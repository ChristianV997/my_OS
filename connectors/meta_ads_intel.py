import requests


class MetaAdsIntel:
    def search_ads(self, keyword, token):
        if not token:
            return 0

        url = "https://graph.facebook.com/v19.0/ads_archive"
        params = {
            "search_terms": keyword,
            "ad_type": "ALL",
            "ad_active_status": "ALL",
            "access_token": token,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        return len(payload.get("data", []))

    def competition_score(self, keyword, token):
        ads = self.search_ads(keyword, token)
        return {"ads_count": ads, "density": min(1.0, ads / 100)}
