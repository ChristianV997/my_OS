MIN_SPEND_FOR_KILL = 10
KILL_ROAS_THRESHOLD = 0.8
MIN_CTR_THRESHOLD = 0.01


def should_kill(event):
    spend = event.get("spend", event.get("cost", 0))

    if spend > MIN_SPEND_FOR_KILL and event.get("roas", 0) < KILL_ROAS_THRESHOLD:
        return True

    if event.get("ctr", 1.0) < MIN_CTR_THRESHOLD:
        return True

    return False
