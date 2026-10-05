import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import json

# --- CONFIGURATION STREAMLIT ---
st.set_page_config(
    page_title="Terminal SMC | Trade Republic Style",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE TRADE REPUBLIC (NOIR PUR) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    .tr-asset-name {
        font-size: 0.9rem;
        font-weight: 500;
        color: #71717a;
        margin-bottom: 2px;
    }
    .tr-price {
        font-family: 'Inter', sans-serif;
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: #ffffff;
        line-height: 1.1;
    }
    .tr-variation {
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 4px;
        margin-bottom: 16px;
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
        letter-spacing: 0.06em;
        color: #71717a;
        margin-bottom: 8px;
    }
    .badge-bull {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-bear {
        background: rgba(244, 63, 94, 0.15);
        color: #f43f5e;
        border: 1px solid rgba(244, 63, 94, 0.35);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    div[data-baseweb="select"] > div {
        background-color: #09090b !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SÉLECTEURS ---
c_sel1, c_sel2, c_sel3 = st.columns([2, 1, 1])

with c_sel1:
    asset_label = st.selectbox(
        "Marché",
        ["BTC/USD", "EUR/USD", "ETH/USD", "SOL/USD", "XAU/USD (Or)", "XAG/USD (Argent)", "NASDAQ 100"],
        index=0,
        label_visibility="collapsed"
    )
with c_sel2:
    timeframe = st.selectbox(
        "Horizon",
        ["1m", "5m", "15m", "1h", "4h"],
        index=1,
        label_visibility="collapsed"
    )
with c_sel3:
    period_options = ["1d", "5d", "7d"] if timeframe == "1m" else ["5d", "1mo", "60d"]
    period = st.selectbox(
        "Historique",
        period_options,
        index=0 if timeframe == "1m" else 0,
        label_visibility="collapsed"
    )

ticker_map = {
    "EUR/USD": "EURUSD=X",
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
    "SOL/USD": "SOL-USD",
    "XAU/USD (Or)": "GC=F",
    "XAG/USD (Argent)": "SI=F",
    "NASDAQ 100": "NQ=F"
}
selected_symbol = ticker_map[asset_label]

# --- CHARGEMENT DU FLUX ---
@st.cache_data(ttl=20, show_spinner=False)
def load_market_data(symbol, interval, lookback):
    try:
        df = yf.download(symbol, period=lookback, interval=interval, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close']].dropna()
        df = df[~df.index.duplicated(keep='first')]
        df.sort_index(inplace=True)
        return df
    except Exception:
        return None

df = load_market_data(selected_symbol, timeframe, period)

if df is None or len(df) < 30:
    st.error("Données indisponibles. Sélectionne un autre horizon.")
    st.stop()

# --- DÉTECTION SMC EXACTE SUR EXTRÊMES ABSOLUS ---
def scan_institutional_order_blocks(data, swing_length=8, post_touch_limit=10):
    obs = []
    n = len(data)
    highs = data['High'].values
    lows = data['Low'].values
    closes = data['Close'].values
    opens = data['Open'].values
    times = data.index

    tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))
    atr = pd.Series(tr).rolling(14).mean().bfill().values

    for i in range(swing_length, n - 4):
        # 1. BEARISH OB (SOMMET ABSOLU)
        is_swing_high = (highs[i] >= np.max(highs[max(0, i - swing_length):i])) and \
                        (highs[i] > np.max(highs[i + 1:min(n, i + swing_length)]))

        if is_swing_high:
            # Recherche de la dernière bougie verte au plus près de la pointe du sommet
            target_idx = None
            for k in range(i, max(0, i - 3), -1):
                if closes[k] >= opens[k]:
                    target_idx = k
                    break
            if target_idx is None:
                target_idx = i

            ob_high = float(highs[i])  # Borne haute = mèche absolue du sommet
            ob_low = float(min(opens[target_idx], closes[target_idx]))

            # Impulsion baissière puissante quittant le sommet
            impulse_idx = i + 1
            body_bear = opens[impulse_idx] - closes[impulse_idx]
            is_impulsive = (body_bear >= (1.1 * atr[impulse_idx])) or ((opens[i+1] - closes[i+2]) >= (1.5 * atr[i+1]))

            # BOS baissier : cassure sous la base précédente
            prior_low = np.min(lows[max(0, i - swing_length):i])
            has_bos = (closes[impulse_idx] < prior_low) or (closes[min(n-1, impulse_idx + 1)] < prior_low)
            has_fvg = (impulse_idx + 1 < n) and (highs[impulse_idx + 1] < ob_low)

            if is_impulsive and (has_bos or has_fvg):
                future_highs = highs[impulse_idx + 1:]
                future_closes = closes[impulse_idx + 1:]

                broken = np.any(future_closes > ob_high) if len(future_closes) > 0 else False
                
                touch_idx = None
                for idx, h in enumerate(future_highs):
                    if h >= ob_low:
                        touch_idx = idx
                        break

                show_zone = not broken
                tested = False
                if touch_idx is not None:
                    tested = True
                    if (len(future_highs) - 1 - touch_idx) > post_touch_limit:
                        show_zone = False

                if show_zone:
                    obs.append({
                        "type": "ZONE VENTE",
                        "high": ob_high,
                        "low": ob_low,
                        "start_time": int(times[target_idx].timestamp()),
                        "tested": tested,
                        "border": "#f43f5e"
                    })

        # 2. BULLISH OB (CREUX ABSOLU)
        is_swing_low = (lows[i] <= np.min(lows[max(0, i - swing_length):i])) and \
                       (lows[i] < np.min(lows[i + 1:min(n, i + swing_length)]))

        if is_swing_low:
            # Recherche de la dernière bougie rouge au plus près du creux
            target_idx = None
            for k in range(i, max(0, i - 3), -1):
                if closes[k] <= opens[k]:
                    target_idx = k
                    break
            if target_idx is None:
                target_idx = i

            ob_high = float(max(opens[target_idx], closes[target_idx]))
            ob_low = float(lows[i])  # Borne basse = mèche absolue du creux

            impulse_idx = i + 1
            body_bull = closes[impulse_idx] - opens[impulse_idx]
            is_impulsive = (body_bull >= (1.1 * atr[impulse_idx])) or ((closes[i+2] - opens[i+1]) >= (1.5 * atr[i+1]))

            prior_high = np.max(highs[max(0, i - swing_length):i])
            has_bos = (closes[impulse_idx] > prior_high) or (closes[min(n-1, impulse_idx + 1)] > prior_high)
            has_fvg = (impulse_idx + 1 < n) and (lows[impulse_idx + 1] > ob_high)

            if is_impulsive and (has_bos or has_fvg):
                future_lows = lows[impulse_idx + 1:]
                future_closes = closes[impulse_idx + 1:]

                broken = np.any(future_closes < ob_low) if len(future_closes) > 0 else False
                
                touch_idx = None
                for idx, l in enumerate(future_lows):
                    if l <= ob_high:
                        touch_idx = idx
                        break

                show_zone = not broken
                tested = False
                if touch_idx is not None:
                    tested = True
                    if (len(future_lows) - 1 - touch_idx) > post_touch_limit:
                        show_zone = False

                if show_zone:
                    obs.append({
                        "type": "ZONE ACHAT",
                        "high": ob_high,
                        "low": ob_low,
                        "start_time": int(times[target_idx].timestamp()),
                        "tested": tested,
                        "border": "#10b981"
                    })

    # Dédoublonnage
    unique = []
    seen = set()
    for o in reversed(obs):
        key = (round(o['high'], 4), round(o['low'], 4), o['type'])
        if key not in seen:
            seen.add(key)
            unique.append(o)
    return list(reversed(unique))

zones = scan_institutional_order_blocks(df, swing_length=8, post_touch_limit=10)

# --- STATISTIQUES TRADE REPUBLIC ---
last_price = float(df['Close'].iloc[-1])
first_price = float(df['Open'].iloc[0])
diff = last_price - first_price
diff_pct = (diff / first_price) * 100
is_forex = "EUR" in selected_symbol
fmt = "{:.5f}" if is_forex else "{:,.2f}"

var_color = "#10b981" if diff >= 0 else "#f43f5e"
sign = "+" if diff >= 0 else ""

st.markdown(f"""
<div>
    <div class="tr-asset-name">{asset_label} · {timeframe}</div>
    <div class="tr-price">{fmt.format(last_price)}</div>
    <div class="tr-variation" style="color: {var_color};">
        {sign}{fmt.format(diff)} ({sign}{diff_pct:.2f} %)
    </div>
</div>
""", unsafe_allow_html=True)

# --- PRÉPARATION DES DONNÉES JSON ---
candles_data = []
for t, row in df.iterrows():
    candles_data.append({
        "time": int(t.timestamp()),
        "open": float(row['Open']),
        "high": float(row['High']),
        "low": float(row['Low']),
        "close": float(row['Close'])
    })

candles_json = json.dumps(candles_data)
zones_json = json.dumps(zones)

# --- TRADINGVIEW LIGHTWEIGHT CHARTS OFFICIEL ---
tv_chart_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: 100%;
            height: 100%;
            background-color: #000000;
            overflow: hidden;
        }}
        #tv_chart {{
            width: 100vw;
            height: 520px;
        }}
    </style>
</head>
<body>
    <div id="tv_chart"></div>
    <script>
        window.addEventListener('DOMContentLoaded', () => {{
            const chartContainer = document.getElementById('tv_chart');
            const width = chartContainer.clientWidth || window.innerWidth || 800;

            const chart = LightweightCharts.createChart(chartContainer, {{
                width: width,
                height: 520,
                layout: {{
                    background: {{ type: 'solid', color: '#000000' }},
                    textColor: '#71717a',
                }},
                grid: {{
                    vertLines: {{ color: '#111318' }},
                    horzLines: {{ color: '#111318' }},
                }},
                crosshair: {{
                    mode: LightweightCharts.CrosshairMode.Normal,
                }},
                rightPriceScale: {{
                    borderColor: '#27272a',
                    scaleMargins: {{
                        top: 0.1,
                        bottom: 0.1,
                    }},
                }},
                timeScale: {{
                    borderColor: '#27272a',
                    timeVisible: true,
                    secondsVisible: false,
                }},
            }});

            const candleSeries = chart.addCandlestickSeries({{
                upColor: '#10b981',
                downColor: '#f43f5e',
                borderUpColor: '#10b981',
                borderDownColor: '#f43f5e',
                wickUpColor: '#10b981',
                wickDownColor: '#f43f5e',
            }});

            const candles = {candles_json};
            candleSeries.setData(candles);

            const zones = {zones_json};
            if (candles.length > 0) {{
                const lastCandleTime = candles[candles.length - 1].time;

                zones.forEach(z => {{
                    if (z.start_time <= lastCandleTime) {{
                        const highLine = chart.addLineSeries({{
                            color: z.border,
                            lineWidth: 1,
                            lineStyle: z.tested ? 2 : 0,
                            priceLineVisible: false,
                            lastValueVisible: false,
                        }});
                        highLine.setData([
                            {{ time: z.start_time, value: z.high }},
                            {{ time: lastCandleTime, value: z.high }}
                        ]);

                        const lowLine = chart.addLineSeries({{
                            color: z.border,
                            lineWidth: 1,
                            lineStyle: z.tested ? 2 : 0,
                            priceLineVisible: false,
                            lastValueVisible: false,
                        }});
                        lowLine.setData([
                            {{ time: z.start_time, value: z.low }},
                            {{ time: lastCandleTime, value: z.low }}
                        ]);
                    }}
                }});
            }}

            chart.timeScale().fitContent();

            window.addEventListener('resize', () => {{
                chart.applyOptions({{ width: chartContainer.clientWidth }});
            }});
        }});
    </script>
</body>
</html>
"""

components.html(tv_chart_html, height=530)

# --- CARTES DE SURVEILLANCE ---
col1, col2 = st.columns(2)
bull_obs = [z for z in zones if z['type'] == "ZONE ACHAT"]
bear_obs = [z for z in zones if z['type'] == "ZONE VENTE"]

with col1:
    st.markdown("""<div class="tr-card"><div class="tr-card-header">Structure Acheteuse (Demand)</div>""", unsafe_allow_html=True)
    if bull_obs:
        for ob in reversed(bull_obs[-2:]):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                <span class="badge-bull">ZONE ACHAT</span>
                <span style="font-family:'JetBrains Mono', monospace; font-size:0.9rem; color:#f4f4f5;">
                    {fmt.format(ob['low'])} — {fmt.format(ob['high'])}
                </span>
                <span style="font-size:0.75rem; color:#71717a;">{'En test' if ob['tested'] else 'Vierge'}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#52525b; font-size:0.85rem; margin-top:4px;'>Aucune zone active</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("""<div class="tr-card"><div class="tr-card-header">Structure Vendeuse (Supply)</div>""", unsafe_allow_html=True)
    if bear_obs:
        for ob in reversed(bear_obs[-2:]):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                <span class="badge-bear">ZONE VENTE</span>
                <span style="font-family:'JetBrains Mono', monospace; font-size:0.9rem; color:#f4f4f5;">
                    {fmt.format(ob['low'])} — {fmt.format(ob['high'])}
                </span>
                <span style="font-size:0.75rem; color:#71717a;">{'En test' if ob['tested'] else 'Vierge'}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#52525b; font-size:0.85rem; margin-top:4px;'>Aucune zone active</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
