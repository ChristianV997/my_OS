MANUAL_CREATIVES = {}


def inject(product_id, creatives):
    MANUAL_CREATIVES[product_id] = creatives


def get_creatives(product_id, generated):
    if product_id in MANUAL_CREATIVES:
        return MANUAL_CREATIVES[product_id]
    return generated
