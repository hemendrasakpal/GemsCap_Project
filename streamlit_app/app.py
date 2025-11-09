import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import json

API_BASE = "http://127.0.0.1:8000/api"

st.set_page_config(layout="wide")
st.title("GemsCap Quant — Indicators & Pair Tools")

# -------------------------------
# Section 1: Single Symbol OHLC Chart
# -------------------------------
st.subheader("📈 Single Symbol OHLC Data")

symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
selected_symbol = st.selectbox("Select Symbol", symbols, index=0)
cols = st.columns([2,1])

if st.button("Fetch OHLC Data"):
    ohlc_url = f"http://127.0.0.1:8000/api/ohlc?symbol={selected_symbol.lower()}"
    st.write(f"Fetching data from `{ohlc_url}` ...")
    r = requests.get(ohlc_url)
    if r.status_code == 200:
        df = pd.DataFrame(r.json())
        if not df.empty:

            time_col = next(
                (c for c in df.columns if c.lower() in ['time', 'timestamp', 'datetime', 'ts', 'index', 'date']), None)

            if time_col:
                df["time"] = pd.to_datetime(df[time_col], errors="coerce")
            else:
                # if no suitable column found, try to use index
                df["time"] = pd.to_datetime(df.index, errors="coerce")

            fig = go.Figure(data=[go.Candlestick(
                x=df["time"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"]
            )])
            fig.update_layout(
                title=f"{selected_symbol} OHLC Chart",
                xaxis_title="Time",
                yaxis_title="Price (USDT)",
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df.tail(10))
        else:
            st.warning("No data returned for this symbol.")
    else:
        st.error(f"API error: {r.status_code}")
        st.text(r.text)

# -------------------------------
# Section 2: Pair Analytics
# -------------------------------
st.markdown("---")
st.subheader("🔍 Pair Analytics")

col1, col2 = st.columns(2)
with col1:
    x_symbol = st.selectbox("Select Base Symbol (X)", symbols, index=0)
with col2:
    y_symbol = st.selectbox("Select Comparison Symbol (Y)", symbols, index=1)

window = st.slider("Window Size", min_value=10, max_value=300, value=60, step=10)
tf = st.selectbox("Timeframe", ["1s", "1m", "5m", "15m", "1h"], index=0)

if st.button("Compute Pair Analytics"):
    api_url = f"http://127.0.0.1:8000/api/pair_analytics?x={x_symbol.lower()}&y={y_symbol.lower()}&tf={tf}&window={window}"
    st.write(f"Fetching from `{api_url}` ...")
    try:
        res = requests.get(api_url)
        if res.status_code == 200:
            data = res.json()
            st.success("✅ Pair analytics computed successfully!")
            st.json(data)

            # Optional: visualize z-score or ratio
            if "zscore" in data:
                st.line_chart(pd.Series(data["zscore"], name="Z-Score"))
        else:
            st.error(f"Server returned {res.status_code}")
            st.text(res.text)
    except Exception as e:
        st.error(f"Request failed: {e}")

with cols[0]:
    st.subheader("Multi-Chart View")
    selected = st.multiselect("Choose symbols (multi-chart)", symbols, default=["BTCUSDT","ETHUSDT"])
    tf = st.selectbox("Timeframe", ['1s', '1m', '5m'], index=1)
    if st.button("Load Multi Charts"):
        # For each symbol, fetch OHLC (tf)
        charts = []
        for s in selected:
            r = requests.get(f"{API_BASE}/ohlc", params={'symbol':s.lower(), 'tf':tf})
            if r.status_code != 200:
                st.error(f"{s} failed: {r.status_code}")
                continue
            df = pd.DataFrame(r.json())
            if df.empty:
                st.warning(f"No data for {s}")
                continue
            # try to detect time column
            time_col = next((c for c in df.columns if c.lower() in ['time','timestamp','index','ts','date','datetime']), None)
            if time_col is None:
                df['time'] = pd.to_datetime(df.index)
            else:
                df['time'] = pd.to_datetime(df[time_col], errors='coerce')
            # compute indicators client-side (or call API)
            df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name=s))
            fig.add_trace(go.Line(x=df['time'], y=df['ema_20'], name='EMA20'))
            fig.update_layout(height=300, title=s, template='plotly_dark', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

with cols[1]:
    st.subheader("Correlation Heatmap")
    sel_corr = st.multiselect("Symbols for correlation", symbols, default=["BTCUSDT","ETHUSDT","BNBUSDT"])
    tf_corr = st.selectbox("Corr timeframe", ['1s', '1m', '5m'], index=1)
    if st.button("Compute Correlation Heatmap"):
        payload = {"symbols":[s.lower() for s in sel_corr], "tf": tf_corr}
        r = requests.post(f"{API_BASE}/corr_heatmap", json=payload)
        if r.status_code == 200:
            corr = r.json().get('corr', {})
            # convert to DataFrame for plotting
            corr_df = pd.DataFrame(corr).reindex(index=[s.lower() for s in sel_corr], columns=[s.lower() for s in sel_corr])
            st.dataframe(corr_df)
            st.write("Heatmap")
            fig = go.Figure(data=go.Heatmap(z=corr_df.values, x=corr_df.columns, y=corr_df.index, colorbar=dict(title="corr")))
            fig.update_layout(template='plotly_dark', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Failed to compute correlation")

st.markdown("---")
st.subheader("Pair: Cointegration & Z-Score")
colx, coly = st.columns(2)
with colx:
    sx = st.selectbox("X symbol", symbols, index=0)
with coly:
    sy = st.selectbox("Y symbol", symbols, index=1)
win = st.slider("Zscore window", 10, 200, 60)

if st.button("Compute Pair Cointegration"):
    r = requests.get(f"{API_BASE}/pair_cointegration", params={'x': sx.lower(), 'y': sy.lower(), 'tf': tf, 'window': win})
    if r.status_code == 200:
        res = r.json()
        st.json({'beta':res.get('beta'),'alpha':res.get('alpha'),'half_life':res.get('half_life')})
        # plot last zscore
        zs = res.get('zscore_series', [])
        sp = res.get('spread_series', [])
        if zs:
            dfz = pd.DataFrame({'z': zs})
            st.line_chart(dfz['z'])
        if sp:
            st.line_chart(pd.Series(sp, name='spread'))
    else:
        st.error("Server error")