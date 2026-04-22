from api.control import STATE


def can_launch(product_id):
    return product_id in STATE["approved_products"]
