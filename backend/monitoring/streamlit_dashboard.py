import streamlit as st
import pandas as pd
import json
from pathlib import Path

LOG_PATH = Path(__file__).resolve().with_name("health_logs.jsonl")

st.set_page_config(page_title="System Health Dashboard", layout="wide")

st.title("📊 Intelligence System Health Dashboard")


def load_data():
    if not LOG_PATH.exists():
        return pd.DataFrame()

    data = []
    with open(LOG_PATH, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    return pd.DataFrame(data)


df = load_data()

if df.empty:
    st.warning("No data yet...")
else:
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("ROAS Over Time")
        st.line_chart(df.set_index("timestamp")["avg_roas"])

        st.subheader("Prediction Error")
        st.line_chart(df.set_index("timestamp")["prediction_error"])

    with col2:
        st.subheader("Novelty Weight")
        st.line_chart(df.set_index("timestamp")["novelty_weight"])

        st.subheader("Diversity")
        st.line_chart(df.set_index("timestamp")["diversity"])

    st.subheader("Latest Metrics")
    st.dataframe(df.tail(5))

if st.sidebar.button("Refresh now"):
    st.rerun()
