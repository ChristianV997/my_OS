def detect(event):
    alerts = []

    if event.get("roas", 0) < 0.7:
        alerts.append("ROAS_DROP")

    if event.get("spend", 0) > 50 and event.get("roas", 0) < 1:
        alerts.append("SPEND_SPIKE")

    return alerts
