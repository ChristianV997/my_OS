"""
MarketOS Live Dashboard — run with:
    streamlit run backend/monitoring/streamlit_dashboard.py

Reads live data directly from the DuckDB state file (state/state.db).
Auto-refreshes every 30 seconds.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

STATE_PATH = os.environ.get("STATE_PATH", "state/state.db")
REFRESH_INTERVAL = 30  # seconds

st.set_page_config(
    page_title="MarketOS Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("MarketOS — Live Decision System Dashboard")


# ── data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=REFRESH_INTERVAL)
def load_event_log(state_path: str, limit: int = 500) -> pd.DataFrame:
    if not os.path.exists(state_path):
        return pd.DataFrame()
    try:
        import duckdb
        con = duckdb.connect(state_path, read_only=True)
        df = con.execute(
            f"""
            SELECT id, roas, prediction, error, pred_width, interval_conf,
                   cost, revenue, env_regime, env_trend
            FROM event_log
            ORDER BY id DESC
            LIMIT {limit}
            """
        ).df()
        con.close()
        return df.sort_values("id").reset_index(drop=True)
    except Exception as e:
        st.warning(f"Could not read event_log: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=REFRESH_INTERVAL)
def load_system_meta(state_path: str) -> dict:
    if not os.path.exists(state_path):
        return {}
    try:
        import duckdb
        con = duckdb.connect(state_path, read_only=True)
        row = con.execute(
            "SELECT * FROM system_meta ORDER BY saved_at DESC LIMIT 1"
        ).fetchone()
        con.close()
        if row is None:
            return {}
        cols = [
            "capital", "regime", "detected_regime",
            "energy_fatigue", "energy_load", "total_cycles",
            "env_trend", "env_regime", "saved_at",
        ]
        return dict(zip(cols, row))
    except Exception:
        return {}


@st.cache_data(ttl=REFRESH_INTERVAL)
def load_causal_edges(state_path: str) -> pd.DataFrame:
    if not os.path.exists(state_path):
        return pd.DataFrame()
    try:
        import duckdb
        con = duckdb.connect(state_path, read_only=True)
        df = con.execute(
            "SELECT parent, child, weight FROM graph_edges ORDER BY ABS(weight) DESC LIMIT 20"
        ).df()
        con.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=REFRESH_INTERVAL)
def load_drift_report() -> dict:
    """Load latest drift report JSON if it exists."""
    for candidate in ["drift_report.json", "state/drift_report.json"]:
        if os.path.exists(candidate):
            try:
                with open(candidate) as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


# ── sidebar controls ──────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")
    state_path = st.text_input("State DB path", value=STATE_PATH)
    window = st.slider("Event window (rows)", min_value=50, max_value=500, value=200, step=50)
    if st.button("Force refresh"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Auto-refreshes every {REFRESH_INTERVAL}s")

# ── load data ─────────────────────────────────────────────────────────────────

meta = load_system_meta(state_path)
df = load_event_log(state_path, limit=window)
edges_df = load_causal_edges(state_path)
drift = load_drift_report()

if not os.path.exists(state_path):
    st.error(f"No state DB found at `{state_path}`. Run `scripts/run_cycles.py` first.")
    st.stop()

if df.empty:
    st.warning("Event log is empty — system has not run yet.")
    st.stop()

# ── top metrics row ───────────────────────────────────────────────────────────

col1, col2, col3, col4, col5 = st.columns(5)

avg_roas = df["roas"].mean() if "roas" in df else 0.0
total_cycles = meta.get("total_cycles", "—")
capital = meta.get("capital", "—")
detected_regime = meta.get("detected_regime", "—")
avg_error = df["error"].abs().mean() if "error" in df else 0.0

col1.metric("Avg ROAS", f"{avg_roas:.4f}")
col2.metric("Total Cycles", f"{total_cycles:,}" if isinstance(total_cycles, int) else total_cycles)
col3.metric("Capital", f"${capital:,.2f}" if isinstance(capital, float) else capital)
col4.metric("Detected Regime", str(detected_regime).capitalize())
col5.metric("Avg |Pred Error|", f"{avg_error:.4f}")

st.divider()

# ── ROAS & prediction error charts ───────────────────────────────────────────

row1_left, row1_right = st.columns(2)

with row1_left:
    st.subheader("ROAS Over Time")
    roas_df = df[["id", "roas"]].set_index("id")
    # rolling 20-event average overlay
    roas_df["roas_ma20"] = roas_df["roas"].rolling(20, min_periods=1).mean()
    st.line_chart(roas_df)

with row1_right:
    st.subheader("Prediction Error Over Time")
    if "error" in df.columns:
        err_df = df[["id", "error"]].set_index("id")
        err_df["abs_error"] = err_df["error"].abs()
        st.line_chart(err_df[["abs_error"]])
    else:
        st.info("No prediction error data yet.")

# ── uncertainty & budget ──────────────────────────────────────────────────────

row2_left, row2_right = st.columns(2)

with row2_left:
    st.subheader("Prediction Interval Width (Uncertainty)")
    if "pred_width" in df.columns and df["pred_width"].notna().any():
        pw_df = df[["id", "pred_width"]].dropna().set_index("id")
        st.line_chart(pw_df)
    else:
        st.info("Conformal intervals not yet available (need ≥30 events for MAPIE).")

with row2_right:
    st.subheader("Cost per Decision (Budget Allocation)")
    if "cost" in df.columns:
        cost_df = df[["id", "cost"]].set_index("id")
        st.line_chart(cost_df)
    else:
        st.info("No cost data.")

# ── environment regime & trend ────────────────────────────────────────────────

st.subheader("Environment — Regime & Trend")

if "env_regime" in df.columns and "env_trend" in df.columns:
    regime_col, trend_col = st.columns(2)

    with regime_col:
        regime_counts = df["env_regime"].value_counts().rename_axis("Regime").reset_index(name="Count")
        st.dataframe(regime_counts, use_container_width=True, hide_index=True)

    with trend_col:
        trend_df = df[["id", "env_trend"]].set_index("id")
        st.line_chart(trend_df)

# ── causal graph ──────────────────────────────────────────────────────────────

st.subheader("Causal Graph — Top Edges (Granger causality)")

if not edges_df.empty:
    edges_df["weight"] = edges_df["weight"].round(4)
    st.dataframe(
        edges_df.rename(columns={"parent": "Feature", "child": "Target", "weight": "Granger strength"}),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No causal edges learned yet.")

# ── drift detection status ────────────────────────────────────────────────────

st.subheader("Drift Detection (Evidently)")

if drift:
    any_drift = drift.get("any_drift", False)
    drift_status = "🔴 DRIFT DETECTED" if any_drift else "🟢 No drift"
    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.metric("Status", drift_status)
    col_d2.metric("Total Events Analysed", drift.get("total_events", "—"))
    col_d3.metric("Drifted Features", f"{drift.get('share_drifted', 0):.0%}")

    if "columns" in drift:
        drift_rows = [
            {"Feature": col, "p-value": info.get("p_value", "—"), "Drifted": "Yes" if info.get("drifted") else "No"}
            for col, info in drift["columns"].items()
        ]
        st.dataframe(pd.DataFrame(drift_rows), use_container_width=True, hide_index=True)
else:
    st.info("No drift report found. Run `scripts/drift_report.py --out drift_report.json` to generate one.")

# ── system meta details ───────────────────────────────────────────────────────

with st.expander("System metadata"):
    if meta:
        st.json(meta)
    else:
        st.write("No metadata available.")

# ── raw event log tail ────────────────────────────────────────────────────────

with st.expander("Latest 20 events"):
    st.dataframe(df.tail(20), use_container_width=True, hide_index=True)

# auto-refresh
st.caption(f"Showing last {len(df)} events from `{state_path}`")
