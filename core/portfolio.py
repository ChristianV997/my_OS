portfolio = {}


def update_portfolio(product_id, metrics):
    portfolio[product_id] = metrics


def allocate_budget(portfolio_data):
    allocations = {}

    total_score = 0
    scores = {}

    for pid, m in portfolio_data.items():
        revenue = m.get("revenue", 0)
        spend = m.get("spend", 0)
        roas = revenue / max(spend, 1)

        score = max(roas, 0.1)
        scores[pid] = score
        total_score += score

    for pid, score in scores.items():
        allocations[pid] = score / total_score if total_score > 0 else 0.0

    return allocations
