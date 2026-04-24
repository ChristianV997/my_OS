from connectors.tiktok_ads import create_campaign


def launch_ads_for_product(product_name, budget=20.0):
    campaign = create_campaign(name=f"{product_name} Campaign", budget=budget)
    return campaign
