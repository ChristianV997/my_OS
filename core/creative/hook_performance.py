from collections import defaultdict


def evaluate_hooks(results: list[dict]) -> dict[str, float]:
    """Return average ROAS per hook string from a list of result records.

    Each record must contain ``"hook"`` and ``"roas"`` keys.
    """
    scores: dict[str, list] = defaultdict(list)

    for r in results:
        hook = r.get("hook", "")
        roas = r.get("roas", 0.0)
        scores[hook].append(roas)

    return {h: sum(v) / len(v) for h, v in scores.items()}
