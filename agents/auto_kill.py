def should_kill(event):
    if event.get("spend", 0) > 10 and event.get("roas", 0) < 0.8:
        return True

    if event.get("ctr", 1.0) < 0.01:
        return True

    return False
