import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="GemsCap Quant Analytics", layout="wide")

API_BASE = "http://127.0.0.1:8000/api"

st.title("📊 GemsCap Quant Analytics Dashboard")

col1, col2 = st.columns(2)
with col1:
    sym_y = st.text_input("Symbol Y", "btcusdt")
with col2:
    sym_x = st.text_input("Symbol X", "ethusdt")

tf = st.selectbox("Timeframe", ['1s', '1min', '5min'], index=1)
window = st.slider("Rolling window", min_value=10, max_value=240, value=60)

if st.button("Compute Pair Analytics"):
    r = requests.get(f"{API_BASE}/pair_analytics", params={'y': sym_y, 'x': sym_x, 'tf': tf, 'window': window})
    st.json(r.json())

if st.button("Plot OHLC"):
    r = requests.get(f"{API_BASE}/ohlc", params={'symbol': sym_y, 'tf': tf})
    df = pd.DataFrame(r.json())
    if not df.empty:
        df['ts'] = pd.to_datetime(df['ts'])
        fig = px.line(df, x='ts', y='close', title=f"{sym_y.upper()} Close Price")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data yet — start the collector first.")
