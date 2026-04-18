def detect(event):
    alerts = []
    spend = event.get("spend", event.get("cost", 0))

    if event.get("roas", 0) < 0.7:
        alerts.append("ROAS_DROP")

    if spend > 50 and event.get("roas", 0) < 1:
        alerts.append("SPEND_SPIKE")

    return alerts
