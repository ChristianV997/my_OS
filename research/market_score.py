def score(opportunity, competition, economics):
    return (
        opportunity["simulation"]["roas"] * 0.4
        + (1 - competition["ad_density"]) * 0.3
        + economics["margin_pct"] * 0.3
    )
