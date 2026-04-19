import os

import numpy as np
import pandas as pd

try:  # pragma: no cover
    from dowhy import CausalModel
except (ImportError, ModuleNotFoundError):  # pragma: no cover
    CausalModel = None

DOWHY_ENABLED = os.getenv("DOWHY_ENABLED", "false").lower() == "true"
DOWHY_SKIP_REFUTATION = os.getenv("DOWHY_SKIP_REFUTATION", "true").lower() == "true"
INTERVENTION_COLUMNS = ("variant", "intensity", "campaign_id")


def _coerce_treatment(df, column):
    if column == "campaign_id":
        extracted = df[column].astype(str).str.replace(r"[^0-9]", "", regex=True)
        return pd.to_numeric(extracted.replace("", np.nan), errors="coerce").fillna(0.0)
    return pd.to_numeric(df[column], errors="coerce").fillna(0.0)


def update_causal(graph, event_log):

    data = event_log.rows[-100:]
    if len(data) < 10:
        return graph

    df = pd.DataFrame(data)
    if "roas" not in df.columns:
        return graph

    roas = pd.to_numeric(df["roas"], errors="coerce").fillna(0.0)
    if roas.nunique() <= 1:
        return graph

    treatments = []
    for column in INTERVENTION_COLUMNS:
        if column not in df.columns:
            continue
        numeric_series = _coerce_treatment(df, column)
        if numeric_series.nunique() <= 1:
            continue
        treatments.append((column, numeric_series))

    if not treatments:
        return graph

    for column, values in treatments:
        corr = float(np.corrcoef(values.to_numpy(), roas.to_numpy())[0, 1])
        if not np.isnan(corr) and abs(corr) > 0.05:
            graph.add_edge(column, "roas", corr)

    if DOWHY_ENABLED and CausalModel is not None:  # pragma: no cover
        numeric_data = pd.DataFrame({"roas": roas})
        for column, values in treatments:
            numeric_data[column] = values

        for column, _ in treatments:
            try:
                model = CausalModel(data=numeric_data, treatment=column, outcome="roas")
                identified = model.identify_effect(proceed_when_unidentifiable=True)
                estimate = model.estimate_effect(identified, method_name="backdoor.linear_regression")
                value = float(estimate.value) if estimate is not None else 0.0
                if abs(value) > 0.05:
                    graph.add_edge(column, "roas", value)
                if not DOWHY_SKIP_REFUTATION:
                    model.refute_estimate(identified, estimate, method_name="random_common_cause")
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                continue

    return graph
