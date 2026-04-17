def causal_score(action, graph):
    score = 0
    for (p, c), w in graph.edges.items():
        if p in action:
            score += w
    return score
