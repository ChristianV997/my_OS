def unit_economics(product):
    cost = product["cost"]
    sell_price = product.get("price", cost * 3)

    margin = sell_price - cost
    margin_pct = margin / sell_price if sell_price else 0

    return {
        "cost": cost,
        "price": sell_price,
        "margin": margin,
        "margin_pct": margin_pct,
    }
