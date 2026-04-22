def estimate_cac(events):
    total_spend = 0.0
    total_conversions = 0.0

    for event in events or []:
        conversions = getattr(event, "conversions", None)
        spend = getattr(event, "spend", None)

        if isinstance(event, dict):
            conversions = event.get("conversions", conversions)
            spend = event.get("spend", spend)

        conversions = float(conversions or 0)
        if conversions > 0:
            total_spend += float(spend or 0)
            total_conversions += conversions

    if total_conversions <= 0:
        return 0.0

    return total_spend / total_conversions
