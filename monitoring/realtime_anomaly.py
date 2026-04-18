ROAS_DROP_THRESHOLD = 0.7
SPEND_SPIKE_THRESHOLD = 50
SPEND_SPIKE_ROAS_CAP = 1


def detect(event):
    alerts = []
    spend = event.get("spend", event.get("cost", 0))

    if event.get("roas", 0) < ROAS_DROP_THRESHOLD:
        alerts.append("ROAS_DROP")

    if spend > SPEND_SPIKE_THRESHOLD and event.get("roas", 0) < SPEND_SPIKE_ROAS_CAP:
        alerts.append("SPEND_SPIKE")

    return alerts
