import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Graphique Live | SMC", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #000000; color: #ffffff; }
    div[data-baseweb="select"] > div {
        background-color: #09090b !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        color: white !important;
    }
    .tr-card {
        background: #09090b;
        border: 1px solid #18181b;
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 14px;
    }
    .tr-card-header {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #71717a;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    asset = st.selectbox("Actif", ["BTC/USD", "EUR/USD", "ETH/USD", "SOL/USD", "XAU/USD (Or)", "XAG/USD (Argent)", "NASDAQ 100"], index=0)
with c2:
    tf = st.selectbox("Horizon", ["1m", "5m", "15m", "1h", "4h"], index=1)
with c3:
    period = "1d" if tf == "1m" else "5d"

ticker_map = {
    "EUR/USD": "EURUSD=X", "BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD",
    "SOL/USD": "SOL-USD", "XAU/USD (Or)": "GC=F", "XAG/USD (Argent)": "SI=F", "NASDAQ 100": "NQ=F"
}

df = yf.download(ticker_map[asset], period=period, interval=tf, progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df = df[['Open', 'High', 'Low', 'Close']].dropna()
df = df[~df.index.duplicated(keep='first')].sort_index()

# Détection des zones SMC
highs, lows, closes, opens = df['High'].values, df['Low'].values, df['Close'].values, df['Open'].values
times = df.index
tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))
atr = pd.Series(tr).rolling(14).mean().bfill().values

zones = []
n = len(df)
swing_length = 8

for i in range(swing_length, n - 4):
    # Bearish OB
    if (highs[i] >= np.max(highs[max(0, i - swing_length):i])) and (highs[i] > np.max(highs[i + 1:min(n, i + swing_length)])):
        target_idx = i
        for k in range(i, max(0, i - 3), -1):
            if closes[k] >= opens[k]:
                target_idx = k
                break
        ob_high = float(highs[i])
        ob_low = float(min(opens[target_idx], closes[target_idx]))
        if (opens[i+1] - closes[i+1]) >= (1.1 * atr[i+1]):
            if not np.any(closes[i+1:] > ob_high):
                zones.append({"type": "ZONE VENTE", "high": ob_high, "low": ob_low, "start_time": int(times[target_idx].timestamp()), "border": "#f43f5e"})

    # Bullish OB
    if (lows[i] <= np.min(lows[max(0, i - swing_length):i])) and (lows[i] < np.min(lows[i + 1:min(n, i + swing_length)])):
        target_idx = i
        for k in range(i, max(0, i - 3), -1):
            if closes[k] <= opens[k]:
                target_idx = k
                break
        ob_high = float(max(opens[target_idx], closes[target_idx]))
        ob_low = float(lows[i])
        if (closes[i+1] - opens[i+1]) >= (1.1 * atr[i+1]):
            if not np.any(closes[i+1:] < ob_low):
                zones.append({"type": "ZONE ACHAT", "high": ob_high, "low": ob_low, "start_time": int(times[target_idx].timestamp()), "border": "#10b981"})

# Formatage JSON pour le graphique
candles_data = [{"time": int(t.timestamp()), "open": float(r['Open']), "high": float(r['High']), "low": float(r['Low']), "close": float(r['Close'])} for t, r in df.iterrows()]
candles_json = json.dumps(candles_data)
zones_json = json.dumps(zones)

tv_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ width: 100%; height: 100%; background: #000; overflow: hidden; }}
        #tv_chart {{ width: 100vw; height: 520px; }}
    </style>
</head>
<body>
    <div id="tv_chart"></div>
    <script>
        window.addEventListener('DOMContentLoaded', () => {{
            const container = document.getElementById('tv_chart');
            const chart = LightweightCharts.createChart(container, {{
                width: container.clientWidth || 800,
                height: 520,
                layout: {{ background: {{ type: 'solid', color: '#000000' }}, textColor: '#71717a' }},
                grid: {{ vertLines: {{ color: '#111318' }}, horzLines: {{ color: '#111318' }} }},
                crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
                rightPriceScale: {{ borderColor: '#27272a' }},
                timeScale: {{ borderColor: '#27272a', timeVisible: true, secondsVisible: false }}
            }});

            const candleSeries = chart.addCandlestickSeries({{
                upColor: '#10b981', downColor: '#f43f5e',
                borderUpColor: '#10b981', borderDownColor: '#f43f5e',
                wickUpColor: '#10b981', wickDownColor: '#f43f5e'
            }});

            const candles = {candles_json};
            candleSeries.setData(candles);

            const zones = {zones_json};
            if (candles.length > 0) {{
                const lastTime = candles[candles.length - 1].time;
                zones.forEach(z => {{
                    if (z.start_time <= lastTime) {{
                        const hLine = chart.addLineSeries({{ color: z.border, lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
                        hLine.setData([{{ time: z.start_time, value: z.high }}, {{ time: lastTime, value: z.high }}]);
                        const lLine = chart.addLineSeries({{ color: z.border, lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
                        lLine.setData([{{ time: z.start_time, value: z.low }}, {{ time: lastTime, value: z.low }}]);
                    }}
                }});
            }}

            chart.timeScale().fitContent();
            window.addEventListener('resize', () => chart.applyOptions({{ width: container.clientWidth }}));
        }});
    </script>
</body>
</html>
"""

components.html(tv_html, height=530)
