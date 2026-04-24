import random


def simulate_metrics():
    return {
        "ctr": random.uniform(0.01, 0.1),
        "cpc": random.uniform(0.2, 2.0),
        "conversion_rate": random.uniform(0.01, 0.05),
        "roas": random.uniform(0.5, 3.0),
    }
