from backend.monitoring.alerting import send_slack, send_telegram
from monitoring.realtime_anomaly import detect


def process_event(event):
    alerts = detect(event)

    for alert in alerts:
        message = f"⚠️ {alert} → {event.get('product_name', 'unknown')} ROAS: {event.get('roas', 0)}"
        send_telegram(message)
        send_slack(message)

    return alerts
