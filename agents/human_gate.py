from api.control import is_product_approved


def can_launch(product_id):
    return is_product_approved(product_id)
