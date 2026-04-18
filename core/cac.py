def estimate_cac(events):
    spends = []

    for event in events or []:
        conversions = getattr(event, "conversions", None)
        spend = getattr(event, "spend", None)

        if isinstance(event, dict):
            conversions = event.get("conversions", conversions)
            spend = event.get("spend", spend)

        if (conversions or 0) > 0:
            spends.append(float(spend or 0))

    if not spends:
        return 0.0

    return sum(spends) / len(spends)
