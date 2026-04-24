import random


def launch_campaign(product_name, budget=5):
    return {
        "campaign_id": f"cmp_{random.randint(1000, 9999)}",
        "product": product_name,
        "budget": budget,
        "status": "launched",
    }


def scale_campaign(campaign_id):
    return {
        "campaign_id": campaign_id,
        "status": "scaled",
    }


def kill_campaign(campaign_id):
    return {
        "campaign_id": campaign_id,
        "status": "killed",
    }
