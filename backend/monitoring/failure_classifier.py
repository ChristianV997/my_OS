import json

TRACE_PATH = "backend/monitoring/decision_trace.jsonl"
GAP_PATH = "backend/monitoring/reality_gap_log.jsonl"
CONF_PATH = "backend/monitoring/confidence_log.jsonl"


def _load_last(path, n=20):
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        return [json.loads(l) for l in lines[-n:]]
    except Exception:
        return []


def classify_failure():
    decisions = _load_last(TRACE_PATH)
    gaps = _load_last(GAP_PATH)
    confs = _load_last(CONF_PATH)

    if not decisions:
        return "unknown"

    # --- signal collapse ---
    contrib_keys = ["world_model", "causal", "velocity", "advantage"]
    avg = {k: 0 for k in contrib_keys}

    for d in decisions:
        c = d.get("contributions", {})
        for k in contrib_keys:
            avg[k] += c.get(k, 0)

    avg = {k: v / len(decisions) for k, v in avg.items()}

    for k, v in avg.items():
        if v > 0.8:
            return f"signal_collapse:{k}"

    # --- confidence error ---
    if gaps and confs:
        high_gap = [g["reality_gap"] for g in gaps if g.get("reality_gap") is not None]
        high_conf = [c["confidence"] for c in confs]

        if high_gap and high_conf:
            if max(high_gap) > 1.0 and max(high_conf) > 0.7:
                return "confidence_error"

    # --- simulation divergence ---
    if gaps:
        values = [g["reality_gap"] for g in gaps if g.get("reality_gap") is not None]
        if len(values) > 5:
            if values[-1] > values[0] * 1.5:
                return "simulation_divergence"

    # --- parameter instability ---
    if confs:
        vals = [c["confidence"] for c in confs]
        if len(vals) > 5:
            variance = sum((x - sum(vals)/len(vals))**2 for x in vals) / len(vals)
            if variance > 0.05:
                return "parameter_instability"

    return "unknown"
