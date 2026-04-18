import numpy as np

try:
    import pandas as pd
    from dowhy import CausalModel
    DOWHY_AVAILABLE = True
except Exception:
    pd = None
    CausalModel = None
    DOWHY_AVAILABLE = False

CAUSAL_DOWHY_INTERVAL = 25


def _numeric_keys(data):
    if not data:
        return []
    keys = []
    for k in data[0].keys():
        if all(_is_numeric(row.get(k, 0)) for row in data):
            keys.append(k)
    return keys


def _is_numeric(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _correlation_fallback(graph, data, state=None):
    if len(data) < 10:
        return graph

    keys = _numeric_keys(data)
    if not keys or "roas" not in keys:
        return graph

    matrix = np.array([[float(row.get(k, 0)) for k in keys] for row in data])
    roas_idx = keys.index("roas")
    roas_col = matrix[:, roas_idx]

    best_effect = 0.0
    for i, k in enumerate(keys):
        if k == "roas":
            continue
        x = matrix[:, i]
        if np.std(x) == 0 or np.std(roas_col) == 0:
            continue
        corr = float(np.corrcoef(x, roas_col)[0, 1])
        if not np.isnan(corr) and abs(corr) > 0.05:
            graph.add_edge(k, "roas", corr)
            if abs(corr) > abs(best_effect):
                best_effect = corr

    if state is not None:
        state.causal_insights = {
            "method": "correlation_fallback",
            "best_roas_effect": float(best_effect),
            "effects": {
                k: float(w)
                for (k, child), w in graph.edges.items()
                if child == "roas"
            },
        }

    return graph


def _dowhy_update(graph, data, state=None):
    df = pd.DataFrame(data).copy()
    numeric_cols = []
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        if np.issubdtype(df[c].dtype, np.number):
            numeric_cols.append(c)

    df = df[numeric_cols].fillna(0.0)
    if "roas" not in df.columns or len(df) < 20:
        return _correlation_fallback(graph, data, state)

    candidate_treatments = [
        c for c in ["variant", "intensity", "cost", "revenue", "orders", "campaign_id"]
        if c in df.columns and c != "roas"
    ]
    if not candidate_treatments:
        return _correlation_fallback(graph, data, state)

    controls = [c for c in df.columns if c not in set(candidate_treatments + ["roas"])]
    effects = {}
    refutations = {}
    best_effect = 0.0

    for treatment in candidate_treatments:
        graph_text = "digraph { " + " ".join([f"{c} -> roas;" for c in controls]) + f" {treatment} -> roas; " + "}"
        try:
            model = CausalModel(
                data=df,
                treatment=treatment,
                outcome="roas",
                graph=graph_text,
            )
            identified = model.identify_effect(proceed_when_unidentifiable=True)
            estimate = model.estimate_effect(identified, method_name="backdoor.linear_regression")
            effect = float(getattr(estimate, "value", 0.0))
            effects[treatment] = effect
            graph.add_edge(treatment, "roas", effect)
            if abs(effect) > abs(best_effect):
                best_effect = effect

            refute = model.refute_estimate(
                identified,
                estimate,
                method_name="placebo_treatment_refuter",
            )
            refutations[treatment] = str(refute)
        except Exception:
            continue

    if not effects:
        return _correlation_fallback(graph, data, state)

    if state is not None:
        state.causal_insights = {
            "method": "dowhy",
            "best_roas_effect": float(best_effect),
            "effects": effects,
            "refutations": refutations,
        }

    return graph


def update_causal(graph, event_log, state=None):
    data = event_log.rows[-100:]
    if len(data) < 10:
        return graph

    # Prefer DoWhy effect estimation + refutation; fall back to correlation graph when unavailable.
    if DOWHY_AVAILABLE and len(data) >= 60:
        # DoWhy estimation is intentionally throttled to reduce per-cycle latency.
        if state is not None and getattr(state, "total_cycles", 0) % CAUSAL_DOWHY_INTERVAL != 0:
            return _correlation_fallback(graph, data, state)
        return _dowhy_update(graph, data, state)

    return _correlation_fallback(graph, data, state)
