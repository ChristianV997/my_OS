from connectors import tiktok_ads, stripe_connector


# --- TikTok Ads ---

def test_tiktok_fallback_no_credentials(monkeypatch):
    monkeypatch.setattr(tiktok_ads, "ACCESS_TOKEN", None)
    monkeypatch.setattr(tiktok_ads, "ADVERTISER_ID", None)
    result = tiktok_ads.get_ad_spend(last_n_minutes=10)
    assert result["total_spend"] > 0
    assert len(result["campaigns"]) > 0
    assert result["campaigns"][0]["campaign_id"].startswith("tt_")


def test_tiktok_fallback_no_requests(monkeypatch):
    monkeypatch.setattr(tiktok_ads, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(tiktok_ads, "ADVERTISER_ID", "adv123")
    monkeypatch.setattr(tiktok_ads, "_requests", None)
    result = tiktok_ads.get_ad_spend()
    assert result["total_spend"] > 0


def test_tiktok_result_keys(monkeypatch):
    monkeypatch.setattr(tiktok_ads, "ACCESS_TOKEN", None)
    result = tiktok_ads.get_ad_spend()
    for key in ("campaigns", "total_spend", "since", "until"):
        assert key in result


# --- Stripe ---

def test_stripe_fallback_no_credentials(monkeypatch):
    monkeypatch.setattr(stripe_connector, "STRIPE_SECRET_KEY", None)
    result = stripe_connector.get_revenue(last_n_minutes=10)
    assert result["total_revenue"] > 0
    assert len(result["charges"]) > 0


def test_stripe_fallback_no_requests(monkeypatch):
    monkeypatch.setattr(stripe_connector, "STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setattr(stripe_connector, "_requests", None)
    result = stripe_connector.get_revenue()
    assert result["total_revenue"] > 0


def test_stripe_result_keys(monkeypatch):
    monkeypatch.setattr(stripe_connector, "STRIPE_SECRET_KEY", None)
    result = stripe_connector.get_revenue()
    for key in ("charges", "total_revenue", "since", "until"):
        assert key in result


def test_stripe_only_counts_succeeded(monkeypatch):
    monkeypatch.setattr(stripe_connector, "STRIPE_SECRET_KEY", None)
    result = stripe_connector.get_revenue()
    # All fallback charges are "succeeded"
    assert result["total_revenue"] == sum(
        stripe_connector._cents_to_dollars(c["amount"])
        for c in stripe_connector._FALLBACK_CHARGES
        if c["status"] == "succeeded"
    )
