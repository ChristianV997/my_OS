def update_causal(graph, event_log):

    data = event_log.rows[-50:]

    # naive causal signal: correlate keys
    if not data:
        return graph

    keys = list(data[0].keys())

    for k in keys:
        if k != "roas":
            graph.add_edge(k, "roas", 0.1)

    return graph
