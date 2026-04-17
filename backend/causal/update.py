import numpy as np


def update_causal(graph, event_log):

    data = event_log.rows[-100:]

    if len(data) < 10:
        return graph

    keys = list(data[0].keys())

    # build matrix
    matrix = np.array([[row.get(k, 0) for k in keys] for row in data], dtype=float)

    # compute correlations with roas
    if "roas" not in keys:
        return graph

    roas_idx = keys.index("roas")
    roas_col = matrix[:, roas_idx]

    for i, k in enumerate(keys):
        if k == "roas":
            continue
        x = matrix[:, i]
        if np.std(x) == 0 or np.std(roas_col) == 0:
            continue
        corr = float(np.corrcoef(x, roas_col)[0, 1])
        if not np.isnan(corr) and abs(corr) > 0.05:
            graph.add_edge(k, "roas", corr)

    return graph
