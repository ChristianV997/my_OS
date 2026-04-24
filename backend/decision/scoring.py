import os

_META_TOKEN = os.getenv("META_ACCESS_TOKEN", "")


def causal_score(action, graph):
    score = 0
    for (p, c), w in graph.edges.items():
        if p in action:
            score += w
    return score


def competition_penalty(keyword: str, token: str = "") -> float:
    """Return a competition penalty score in [0, 0.2] for *keyword*.

    Queries the Meta Ads Library when ``META_ACCESS_TOKEN`` is set; falls
    back to a neutral 0.1 when the token is absent or the call fails.
    High ad density → higher penalty → lower final decision score.
    """
    effective_token = token or _META_TOKEN
    if not effective_token:
        return 0.1  # neutral fallback

    try:
        from connectors.meta_ads_intel import MetaAdsIntel
        score = MetaAdsIntel().competition_score(keyword, effective_token)
        density = float(score.get("density", 0.5))
    except Exception:
        density = 0.5

    return round(density * 0.2, 4)  # scale density [0,1] to penalty [0, 0.2]

