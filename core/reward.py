def compute_reward(metrics):
    revenue = metrics.get("revenue", 0)
    spend = metrics.get("spend", 0)

    roas = revenue / max(spend, 1)

    return 1 if roas > 1 else 0
